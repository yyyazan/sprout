/* ===========================================================================
 * garden/index.js — Sprout garden view entry point.
 *
 * One plant per portfolio position, growing straight out of the page. GardenView
 * calls initGarden({positions, period}) in onMount and the returned teardown in
 * onDestroy. Everything is organised as LAYERS sharing one scene context:
 *
 *   - context.js builds the renderer/scene/camera/clock once → `ctx`.
 *   - each layer's build(ctx) adds objects and registers per-frame work.
 *   - the loop here iterates ctx._updates, then renders.
 *
 * Add a new visual layer = create layers/foo.js exporting a factory, then add
 * one line to the `layers` array below. Nothing else changes.
 * ======================================================================== */

import { createContext, disposeContext } from "./context.js";
import createLights from "./lighting.js";
import createSky from "./layers/sky.js";
import createGround from "./layers/ground.js";
import createPlants from "./layers/plants.js";
import createInteraction from "./layers/interaction.js";
import createInspect from "./layers/inspect.js";
import createDebug from "./layers/debug.js";
import createEditor, { editorEnabled } from "./layers/editor.js";
import createPick from "./layers/pick.js";

// One live garden at a time. If initGarden runs again before the previous mount
// tore down (defensive against double-mounts / fast navigation), clean up first.
let _activeTeardown = null;

// options.debug → the dedicated /garden debug page: full OrbitControls camera
// (rotate/pan/zoom) instead of the dashboard's idle-sway orbit, editor always
// on, and grid/axes helpers. The dashboard passes no options (band defaults).
export function initGarden(data, options = {}) {
  const root = document.getElementById("garden-root");
  if (!root) return function () {};

  if (_activeTeardown) _activeTeardown();

  const debug = !!options.debug;
  // interactive:false → a purely ambient scene (idle sway only): no hover
  // glow, no click-to-open, no touch drag-to-orbit. Used where there's no
  // portfolio behind the plants, e.g. the sign-in screen.
  const interactive = options.interactive !== false;
  // bare:true → just the pots and plants on a transparent canvas: no sky dome,
  // no ground bed, no sun/moon. The host's own background shows through, so
  // the scene follows the page theme instead of the fixed cream PAGE_BG.
  const bare = !!options.bare;
  const ctx = createContext(root, data);
  ctx.debug = debug;
  ctx.interactive = interactive;
  if (bare) {
    ctx.scene.background = null;
    ctx.renderer.setClearColor(0x000000, 0);
  }

  // Layer registry — order is scene-build order. Append to grow the scene.
  const layers = [
    ...(bare ? [] : [createSky()]),
    createLights(),
    ...(bare ? [] : [createGround()]),
    createPlants(),
    // Camera control depends on context: inspect (OrbitControls) for the debug
    // page, idle-sway orbit for the dashboard band.
    debug ? createInspect() : createInteraction(),
  ];
  if (debug) layers.push(createDebug());
  // Editor (gizmo picking) on the debug page; otherwise the interactive pick
  // layer (hover glow + tooltip + click-to-open + wind sway) on the live heroes.
  const wantEditor = debug || editorEnabled();
  if (wantEditor) layers.push(createEditor());
  else if (interactive)
    layers.push(
      createPick({ onHover: options.onHover, onPick: options.onPick })
    );

  for (const layer of layers) {
    if (layer.build) layer.build(ctx);
    ctx.layers.push(layer);
  }

  let raf = requestAnimationFrame(function loop() {
    raf = requestAnimationFrame(loop);
    const t = ctx.clock.getElapsedTime();
    for (const fn of ctx._updates) fn(t, ctx);
    if (ctx.composer) ctx.composer.render();
    else ctx.renderer.render(ctx.scene, ctx.camera);
  });

  function teardown() {
    cancelAnimationFrame(raf);
    for (const layer of ctx.layers) {
      if (layer.dispose) layer.dispose();
    }
    disposeContext(ctx);
    if (_activeTeardown === teardown) _activeTeardown = null;
  }

  _activeTeardown = teardown;
  return teardown; // GardenView calls this on unmount
}
