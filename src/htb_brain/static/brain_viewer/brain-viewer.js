// brain-viewer.js — <brain-viewer> Web Component
// 3D glass brain with activation glow overlay, post-processing bloom, raycasting tooltips.

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { TooltipSystem } from './tooltip.js';

// We inline the shader sources; they are small enough.
const VERT_SHADER = `
attribute float activation;
attribute float highlight;

varying float vActivation;
varying float vHighlight;
varying vec3 vNormal;
varying vec3 vViewPosition;

void main() {
    vActivation = activation;
    vHighlight  = highlight;
    vNormal = normalize(normalMatrix * normal);

    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    vViewPosition = -mvPosition.xyz;

    gl_Position = projectionMatrix * mvPosition;
}
`;

const FRAG_SHADER = `
precision highp float;

varying float vActivation;
varying float vHighlight;
varying vec3 vNormal;
varying vec3 vViewPosition;

const vec3 COLOR_CYAN   = vec3(0.180, 0.906, 0.714);
const vec3 COLOR_GREEN  = vec3(0.624, 0.937, 0.0);
const vec3 COLOR_BRIGHT = vec3(0.812, 1.0, 0.251);

uniform float uTime;

void main() {
    float a = clamp(vActivation, 0.0, 1.0);

    // Color ramp
    vec3 color;
    if (a <= 0.3) {
        float t = a / 0.3;
        color = COLOR_CYAN * t;
    } else if (a <= 0.6) {
        float t = (a - 0.3) / 0.3;
        color = mix(COLOR_CYAN, COLOR_GREEN, t);
    } else {
        float t = (a - 0.6) / 0.4;
        color = mix(COLOR_GREEN, COLOR_BRIGHT, t);
    }

    // Fresnel rim glow
    vec3 viewDir = normalize(vViewPosition);
    vec3 normal  = normalize(vNormal);
    float fresnel = 1.0 - abs(dot(viewDir, normal));
    fresnel = pow(fresnel, 2.5);
    color += COLOR_CYAN * fresnel * 0.6 * a;

    // Highlight pulse (hovered group)
    float pulse = 0.5 + 0.5 * sin(uTime * 6.0);
    color += vec3(0.3, 0.5, 0.1) * vHighlight * pulse;

    // Alpha
    float alpha = a * (0.65 + fresnel * 0.35);
    alpha += vHighlight * 0.2;

    // Emissive boost for bloom
    color *= 1.0 + a * 1.5;

    if (alpha < 0.005) discard;

    gl_FragColor = vec4(color, alpha);
}
`;

const VERTEX_COUNT = 20484;

class BrainViewer extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });

        // State
        this._activations = null;       // current Float32Array
        this._prevActivations = null;   // previous (for lerp)
        this._targetActivations = null; // target (for lerp)
        this._lerpStart = 0;
        this._lerpDuration = 500; // ms

        this._groupData = [];           // array of {id, name, operator_frame, score}
        this._groupIndexAttr = null;    // per-vertex group index
        this._hoveredGroup = -1;

        this._ready = false;
        this._disposed = false;

        this._highlightArray = null;
    }

    connectedCallback() {
        this._buildDOM();
        this._initThree();

        const meshUrl = this.getAttribute('data-mesh');
        if (meshUrl) {
            this._loadMesh(meshUrl);
        }
    }

    disconnectedCallback() {
        this._disposed = true;
        if (this._animId) cancelAnimationFrame(this._animId);
        if (this._resizeObs) this._resizeObs.disconnect();
        if (this._renderer) this._renderer.dispose();
    }

    // ---- Public API ----

    /**
     * Set activation data (20484 floats, 0-1).
     * Triggers smooth lerp transition from current to new values.
     */
    setActivations(float32Array) {
        if (!(float32Array instanceof Float32Array)) {
            float32Array = new Float32Array(float32Array);
        }

        if (this._activations) {
            this._prevActivations = new Float32Array(this._activations);
        } else {
            this._prevActivations = new Float32Array(float32Array.length);
        }

        this._targetActivations = float32Array;
        this._lerpStart = performance.now();

        // If first load, set immediately
        if (!this._activations) {
            this._activations = new Float32Array(float32Array.length);
        }

        this._updateActivationAttribute();
    }

    /**
     * Set group metadata.
     * @param {Array<{id: number, name: string, operator_frame: string, score: number}>} groupsArray
     */
    setGroupData(groupsArray) {
        this._groupData = groupsArray || [];
    }

    // ---- DOM setup ----

    _buildDOM() {
        // Load CSS
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = new URL('./brain-viewer.css', import.meta.url).href;
        this.shadowRoot.appendChild(link);

        // Loading overlay
        this._loadingEl = document.createElement('div');
        this._loadingEl.classList.add('bv-loading');
        this._loadingEl.innerHTML = `
            <div class="bv-loading-brain"></div>
            <div class="bv-loading-text">Loading mesh...</div>
        `;
        this.shadowRoot.appendChild(this._loadingEl);

        // Color bar legend
        const bar = document.createElement('div');
        bar.classList.add('bv-colorbar');
        bar.innerHTML = `
            <span class="bv-colorbar-label">Low</span>
            <div>
                <div class="bv-colorbar-gradient"></div>
            </div>
            <span class="bv-colorbar-label">High</span>
        `;
        this.shadowRoot.appendChild(bar);

        // Tooltip system
        this._tooltip = new TooltipSystem(this.shadowRoot);
    }

    // ---- Three.js init ----

    _initThree() {
        const w = this.clientWidth || 800;
        const h = this.clientHeight || 600;

        // Renderer
        this._renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
        this._renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this._renderer.setSize(w, h);
        this._renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this._renderer.toneMappingExposure = 1.0;
        this._renderer.outputColorSpace = THREE.SRGBColorSpace;
        this.shadowRoot.appendChild(this._renderer.domElement);

        // Scene
        this._scene = new THREE.Scene();
        this._scene.background = new THREE.Color(0x0A0E27);

        // Camera
        this._camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
        this._camera.position.set(0, 0.5, 2.5);

        // Lights
        const ambient = new THREE.AmbientLight(0x2EE7B6, 0.4);
        this._scene.add(ambient);

        const key = new THREE.DirectionalLight(0xffffff, 0.6);
        key.position.set(2, 3, 1);
        this._scene.add(key);

        const rim = new THREE.DirectionalLight(0x9FEF00, 0.3);
        rim.position.set(-2, 1, -2);
        this._scene.add(rim);

        // Controls
        this._controls = new OrbitControls(this._camera, this._renderer.domElement);
        this._controls.autoRotate = true;
        this._controls.autoRotateSpeed = 2;
        this._controls.enableDamping = true;
        this._controls.dampingFactor = 0.08;
        this._controls.minDistance = 1;
        this._controls.maxDistance = 6;

        // Post-processing
        this._composer = new EffectComposer(this._renderer);
        this._composer.addPass(new RenderPass(this._scene, this._camera));

        const bloom = new UnrealBloomPass(
            new THREE.Vector2(w, h),
            1.5,   // strength
            0.4,   // radius
            0.85   // threshold
        );
        this._composer.addPass(bloom);

        // Raycasting
        this._raycaster = new THREE.Raycaster();
        this._mouse = new THREE.Vector2();

        // Events
        this._renderer.domElement.addEventListener('mousemove', (e) => this._onMouseMove(e));
        this._renderer.domElement.addEventListener('click', (e) => this._onClick(e));
        this._renderer.domElement.addEventListener('mouseleave', () => this._onMouseLeave());

        // Resize observer
        this._resizeObs = new ResizeObserver(() => this._onResize());
        this._resizeObs.observe(this);

        // Start render loop
        this._clock = new THREE.Clock();
        this._animate();
    }

    // ---- Mesh loading ----

    async _loadMesh(url) {
        try {
            const loader = new GLTFLoader();
            const gltf = await new Promise((resolve, reject) => {
                loader.load(url, resolve, undefined, reject);
            });

            let geometry = gltf.scene.children[0]?.geometry;
            if (!geometry) {
                // Traverse to find the first mesh
                gltf.scene.traverse((child) => {
                    if (child.isMesh && !geometry) {
                        geometry = child.geometry;
                    }
                });
            }

            if (!geometry) {
                console.error('BrainViewer: No geometry found in GLB');
                return;
            }

            // Save the _GROUPINDEX attribute
            this._groupIndexAttr = geometry.getAttribute('_GROUPINDEX') || null;

            // Do NOT mergeVertices — it changes vertex count and breaks
            // the 20484 activation array mapping. Just compute normals.
            geometry.computeVertexNormals();

            // Center and scale
            geometry.computeBoundingSphere();
            const center = geometry.boundingSphere.center;
            const radius = geometry.boundingSphere.radius;
            geometry.translate(-center.x, -center.y, -center.z);
            const scale = 1.0 / radius;
            geometry.scale(scale, scale, scale);

            // ---- Layer 1: Glass brain ----
            // Use MeshStandardMaterial with low opacity for reliable translucent look
            const glassMat = new THREE.MeshStandardMaterial({
                color: new THREE.Color(0x2a3555),
                metalness: 0.1,
                roughness: 0.4,
                transparent: true,
                opacity: 0.15,
                side: THREE.DoubleSide,
                depthWrite: false,
            });
            this._glassMesh = new THREE.Mesh(geometry, glassMat);
            this._scene.add(this._glassMesh);

            // ---- Layer 2: Activation glow ----
            const vertCount = geometry.attributes.position.count;

            // Add activation attribute (all zeros initially)
            const activationArr = new Float32Array(vertCount);
            geometry.setAttribute('activation', new THREE.BufferAttribute(activationArr, 1));

            // Add highlight attribute
            this._highlightArray = new Float32Array(vertCount);
            geometry.setAttribute('highlight', new THREE.BufferAttribute(this._highlightArray, 1));

            const glowMat = new THREE.ShaderMaterial({
                vertexShader: VERT_SHADER,
                fragmentShader: FRAG_SHADER,
                uniforms: {
                    uTime: { value: 0 },
                },
                transparent: true,
                blending: THREE.AdditiveBlending,
                depthWrite: false,
                side: THREE.DoubleSide,
            });

            this._glowMesh = new THREE.Mesh(geometry, glowMat);
            this._scene.add(this._glowMesh);

            // Store vertex count
            this._vertexCount = vertCount;

            // If activations were set before mesh loaded, apply now
            if (this._targetActivations) {
                this._updateActivationAttribute();
            }

            this._ready = true;
            this._meshLoaded = true;

            // Hide loading overlay
            this._loadingEl.classList.add('hidden');

            this.dispatchEvent(new CustomEvent('mesh-loaded', { detail: { vertexCount: vertCount } }));

        } catch (err) {
            console.error('BrainViewer: Failed to load mesh', err);
            this._loadingEl.querySelector('.bv-loading-text').textContent = 'Failed to load mesh';
        }
    }

    // ---- Activation attribute update (with lerp) ----

    _updateActivationAttribute() {
        if (!this._glowMesh) return;

        const geom = this._glowMesh.geometry;
        const attr = geom.getAttribute('activation');
        if (!attr) return;

        const count = attr.count;
        const target = this._targetActivations;
        if (!target) return;

        // Immediate set for attribute — lerp happens in _animate
        const len = Math.min(count, target.length);
        for (let i = 0; i < len; i++) {
            attr.array[i] = target[i];
        }
        attr.needsUpdate = true;
    }

    _lerpActivations(now) {
        if (!this._prevActivations || !this._targetActivations || !this._glowMesh) return;

        const elapsed = now - this._lerpStart;
        if (elapsed >= this._lerpDuration) {
            // Done lerping — just use target
            this._activations = this._targetActivations;
            this._prevActivations = null;
            return;
        }

        const t = elapsed / this._lerpDuration;
        const eased = t * t * (3 - 2 * t); // smoothstep

        const attr = this._glowMesh.geometry.getAttribute('activation');
        if (!attr) return;

        const count = Math.min(attr.count, this._targetActivations.length, this._prevActivations.length);
        for (let i = 0; i < count; i++) {
            const v = this._prevActivations[i] + (this._targetActivations[i] - this._prevActivations[i]) * eased;
            attr.array[i] = v;
            this._activations[i] = v;
        }
        attr.needsUpdate = true;
    }

    // ---- Raycasting ----

    _onMouseMove(event) {
        const rect = this._renderer.domElement.getBoundingClientRect();
        this._mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this._mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        this._clientX = event.clientX;
        this._clientY = event.clientY;

        this._doRaycast();
    }

    _onMouseLeave() {
        this._tooltip.hide();
        this._clearHighlight();
        this._hoveredGroup = -1;
    }

    _onClick() {
        if (this._hoveredGroup >= 0) {
            const group = this._groupData.find(g => g.id === this._hoveredGroup);
            if (group) {
                this._tooltip.showDetail(group);
            }
        } else {
            this._tooltip.hideDetail();
        }
    }

    _doRaycast() {
        if (!this._ready || !this._glowMesh) return;

        this._raycaster.setFromCamera(this._mouse, this._camera);
        const intersects = this._raycaster.intersectObject(this._glowMesh, false);

        if (intersects.length > 0) {
            const face = intersects[0].face;
            const faceIndex = intersects[0].faceIndex;

            // Get vertex index from face
            const vertexIndex = face.a; // pick first vertex of face

            // Look up group index
            let groupIdx = -1;
            if (this._groupIndexAttr) {
                groupIdx = this._groupIndexAttr.getX(vertexIndex);
            }

            if (groupIdx >= 0 && groupIdx !== this._hoveredGroup) {
                this._hoveredGroup = groupIdx;
                this._highlightGroup(groupIdx);

                const group = this._groupData.find(g => g.id === groupIdx);
                if (group) {
                    this._tooltip.show(this._clientX, this._clientY, group);
                } else {
                    // Build minimal data from activation values
                    const score = this._activations ? (this._activations[vertexIndex] || 0) : 0;
                    this._tooltip.show(this._clientX, this._clientY, {
                        name: `Region ${groupIdx}`,
                        score,
                        operator_frame: '',
                    });
                }
            } else if (groupIdx >= 0) {
                // Same group, just update position
                const group = this._groupData.find(g => g.id === groupIdx) || {
                    name: `Region ${groupIdx}`,
                    score: this._activations ? (this._activations[vertexIndex] || 0) : 0,
                };
                this._tooltip.show(this._clientX, this._clientY, group);
            } else {
                this._tooltip.hide();
                this._clearHighlight();
                this._hoveredGroup = -1;
            }
        } else {
            this._tooltip.hide();
            this._clearHighlight();
            this._hoveredGroup = -1;
        }
    }

    _highlightGroup(groupIdx) {
        if (!this._highlightArray || !this._groupIndexAttr || !this._glowMesh) return;

        const attr = this._glowMesh.geometry.getAttribute('highlight');
        const groupAttr = this._groupIndexAttr;
        const count = attr.count;

        for (let i = 0; i < count; i++) {
            this._highlightArray[i] = (groupAttr.getX(i) === groupIdx) ? 1.0 : 0.0;
        }
        attr.needsUpdate = true;
    }

    _clearHighlight() {
        if (!this._highlightArray || !this._glowMesh) return;

        const attr = this._glowMesh.geometry.getAttribute('highlight');
        if (!attr) return;

        this._highlightArray.fill(0);
        attr.needsUpdate = true;
    }

    // ---- Resize ----

    _onResize() {
        const w = this.clientWidth;
        const h = this.clientHeight;
        if (w === 0 || h === 0) return;

        this._camera.aspect = w / h;
        this._camera.updateProjectionMatrix();
        this._renderer.setSize(w, h);
        this._composer.setSize(w, h);
    }

    // ---- Render loop ----

    _animate() {
        if (this._disposed) return;
        this._animId = requestAnimationFrame(() => this._animate());

        const now = performance.now();
        const delta = this._clock.getDelta();

        // Lerp activations
        if (this._prevActivations) {
            this._lerpActivations(now);
        }

        // Update uniforms
        if (this._glowMesh) {
            this._glowMesh.material.uniforms.uTime.value = now * 0.001;
        }

        this._controls.update();
        this._composer.render();
    }
}

customElements.define('brain-viewer', BrainViewer);

export { BrainViewer };
