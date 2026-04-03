// activation.vert — Vertex shader for brain activation glow layer

attribute float activation;

varying float vActivation;
varying vec3 vNormal;
varying vec3 vViewPosition;

void main() {
    vActivation = activation;
    vNormal = normalize(normalMatrix * normal);

    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    vViewPosition = -mvPosition.xyz;

    gl_Position = projectionMatrix * mvPosition;
}
