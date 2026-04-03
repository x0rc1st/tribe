// activation.frag — Fragment shader for brain activation glow layer

precision highp float;

varying float vActivation;
varying vec3 vNormal;
varying vec3 vViewPosition;

// HTB color stops
const vec3 COLOR_CYAN       = vec3(0.180, 0.906, 0.714);  // #2EE7B6
const vec3 COLOR_GREEN      = vec3(0.624, 0.937, 0.0);    // #9FEF00
const vec3 COLOR_BRIGHT     = vec3(0.812, 1.0, 0.251);    // boosted bright green

void main() {
    float a = clamp(vActivation, 0.0, 1.0);

    // ---- Color ramp ----
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

    // ---- Fresnel rim glow ----
    vec3 viewDir = normalize(vViewPosition);
    vec3 normal  = normalize(vNormal);
    float fresnel = 1.0 - abs(dot(viewDir, normal));
    fresnel = pow(fresnel, 2.5);

    // Add rim glow — stronger at silhouette edges
    color += COLOR_CYAN * fresnel * 0.6 * a;

    // ---- Alpha ----
    // Zero activation = fully transparent; scales up with activation
    float alpha = a * (0.65 + fresnel * 0.35);

    // Boost color for bloom pass (emissive feel)
    color *= 1.0 + a * 1.5;

    // Kill fully-transparent fragments early
    if (alpha < 0.005) discard;

    gl_FragColor = vec4(color, alpha);
}
