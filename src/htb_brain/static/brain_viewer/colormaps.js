// colormaps.js — HTB color ramp and group color utilities

/**
 * Map a normalized activation value (0-1) to an HTB-themed color.
 * Ramp: 0.0 = transparent, 0.3 = cyan #2EE7B6, 0.6 = green #9FEF00, 1.0 = bright green (high intensity).
 * @param {number} value — activation in [0, 1]
 * @returns {{r: number, g: number, b: number, intensity: number}} color channels in [0,1]
 */
export function activationToColor(value) {
    const v = Math.max(0, Math.min(1, value));

    // Key stops (linear RGB, 0-1)
    const cyan   = { r: 0x2E / 255, g: 0xE7 / 255, b: 0xB6 / 255 }; // #2EE7B6
    const green  = { r: 0x9F / 255, g: 0xEF / 255, b: 0x00 / 255 }; // #9FEF00
    const bright = { r: 0xCF / 255, g: 0xFF / 255, b: 0x40 / 255 }; // boosted bright green

    let r, g, b, intensity;

    if (v <= 0.0) {
        return { r: 0, g: 0, b: 0, intensity: 0 };
    } else if (v <= 0.3) {
        // Fade in from transparent to cyan
        const t = v / 0.3;
        r = cyan.r * t;
        g = cyan.g * t;
        b = cyan.b * t;
        intensity = t * 0.5;
    } else if (v <= 0.6) {
        // Cyan to green
        const t = (v - 0.3) / 0.3;
        r = cyan.r + (green.r - cyan.r) * t;
        g = cyan.g + (green.g - cyan.g) * t;
        b = cyan.b + (green.b - cyan.b) * t;
        intensity = 0.5 + t * 0.3;
    } else {
        // Green to bright green (high intensity)
        const t = (v - 0.6) / 0.4;
        r = green.r + (bright.r - green.r) * t;
        g = green.g + (bright.g - green.g) * t;
        b = green.b + (bright.b - green.b) * t;
        intensity = 0.8 + t * 0.2;
    }

    return { r, g, b, intensity };
}

/**
 * Generate a consistent color for a group id.
 * Useful for radar charts or legends where each brain region group needs a distinct hue.
 * @param {number|string} groupId
 * @returns {{r: number, g: number, b: number, hex: string}}
 */
export function getGroupColor(groupId) {
    // Must match getGroupColor() in brain-viewer.js fragment shader exactly
    const byId = {
        1:  '#00BFFF', // Strategic Thinking — bright blue
        2:  '#9EF000', // Procedural Fluency — lime green
        3:  '#FF9900', // Technical Comprehension — orange
        4:  '#D900FF', // Visual Processing — purple
        5:  '#FFFF00', // Situational Awareness — yellow
        6:  '#FF334D', // Motivation & Adaptive Drive — red
        7:  '#00FF99', // Memory Encoding — mint
        8:  '#2EE8B5', // Knowledge Synthesis — cyan
        9:  '#FF66B3', // Threat Awareness — pink
        10: '#99CCFF', // Deep Internalization — ice blue
    };

    const id = typeof groupId === 'string' ? hashString(groupId) : groupId;
    const hex = byId[id] || '#4D4D4D';

    const bigint = parseInt(hex.slice(1), 16);
    return {
        r: ((bigint >> 16) & 255) / 255,
        g: ((bigint >> 8) & 255) / 255,
        b: (bigint & 255) / 255,
        hex,
    };
}

function hashString(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
    }
    return Math.abs(hash);
}

/**
 * Build a 256-wide RGBA Uint8Array texture data for the activation color ramp.
 * Suitable for use as a DataTexture in Three.js.
 * @returns {Uint8Array} 256 * 4 bytes (RGBA)
 */
export function buildColorRampTextureData() {
    const data = new Uint8Array(256 * 4);
    for (let i = 0; i < 256; i++) {
        const v = i / 255;
        const c = activationToColor(v);
        data[i * 4 + 0] = Math.round(c.r * 255);
        data[i * 4 + 1] = Math.round(c.g * 255);
        data[i * 4 + 2] = Math.round(c.b * 255);
        data[i * 4 + 3] = Math.round(c.intensity * 255);
    }
    return data;
}
