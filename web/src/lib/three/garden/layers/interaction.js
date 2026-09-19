/* ===========================================================================
 * interaction.js — drag-to-orbit camera + gentle idle sway.
 *
 * Manual orbit (kept deliberately instead of OrbitControls) so the bespoke idle
 * sway and lerp-follow that make the scene feel alive stay simple, and so the
 * editor can suppress orbit during a gizmo drag with a single flag check
 * (ctx.state.transformDragging).
 *
 * Future hover/popup interaction lands here too.
 * ======================================================================== */

export default function createInteraction() {
  return {
    name: "interaction",
    build(ctx) {
      const canvas = ctx.canvas;
      const orbit = ctx.state.orbit;

      // Drag-to-orbit is enabled on TOUCH (mobile hero) only. On desktop the
      // camera stays locked to the tuned framing so an accidental drag never
      // fights the plant hover/click interaction (pick.js). The idle sway below
      // still runs everywhere to keep the scene alive.
      const isTouch =
        typeof window !== "undefined" &&
        window.matchMedia &&
        window.matchMedia("(hover: none), (pointer: coarse)").matches;

      // ── Drag-to-orbit (touch only) ──────────────────────────────────────
      // Drag left/right to spin around the bed; drag up to tilt toward the sky,
      // drag down for a more top-down tending view. Elevation is clamped so you
      // never flip under the ground or fully overhead.
      if (isTouch && ctx.interactive !== false) {
        canvas.style.cursor = "grab";
        const last = { x: 0, y: 0 };

        function onDown(e) {
          // Let a TransformControls gizmo drag win the mouse outright, so grabbing
          // an axis handle never also spins the camera.
          if (ctx.state.transformDragging) return;
          orbit.dragging = true;
          last.x = e.clientX;
          last.y = e.clientY;
          canvas.style.cursor = "grabbing";
        }
        function onUp() {
          orbit.dragging = false;
          canvas.style.cursor = "grab";
        }
        function onMove(e) {
          if (ctx.state.transformDragging) return;
          if (!orbit.dragging) return;
          orbit.az += (e.clientX - last.x) * 0.005;
          orbit.el = Math.max(0.04, Math.min(0.95, orbit.el + (e.clientY - last.y) * 0.005));
          last.x = e.clientX;
          last.y = e.clientY;
        }

        ctx.addListener(canvas, "mousedown", onDown);
        ctx.addListener(window, "mouseup", onUp);
        ctx.addListener(canvas, "mousemove", onMove);
      }

      // ── Per-frame orbit ───────────────────────────────────────────────────
      // Idle → a tiny azimuth sway keeps the scene alive; while dragging → follow
      // the user exactly. Lerp so motion never snaps.
      const camera = ctx.camera;
      const target = ctx.state.target;
      ctx.registerUpdate(function (t) {
        const az = orbit.az + (orbit.dragging ? 0 : Math.sin(t * 0.22) * 0.04);
        const r = orbit.radius;
        const dx = target.x + r * Math.cos(orbit.el) * Math.sin(az);
        const dy = target.y + r * Math.sin(orbit.el);
        const dz = target.z + r * Math.cos(orbit.el) * Math.cos(az);
        camera.position.x += (dx - camera.position.x) * 0.08;
        camera.position.y += (dy - camera.position.y) * 0.08;
        camera.position.z += (dz - camera.position.z) * 0.08;
        camera.lookAt(target);
      });
    },
  };
}
