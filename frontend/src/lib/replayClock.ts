/** High-rate scrubber time for R3F useFrame (ms). UI store `t` is throttled. */
export const visualTRef = { current: 0 }

/** True while OrbitControls is actively dragging — freezes the replay clock. */
export const orbitDraggingRef = { current: false }

/** How often Zustand `t` publishes while playing (DOM / HUD / charts). */
export const UI_T_INTERVAL_MS = 80
