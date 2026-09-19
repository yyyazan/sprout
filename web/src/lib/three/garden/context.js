/* ===========================================================================
 * context.js — the shared scene context every layer receives.
 *
 * createContext() builds the renderer / scene / camera / clock once per mount
 * and returns `ctx`, the single object passed into each layer's build(ctx).
 * Layers create objects on ctx.scene, register per-frame work with
 * ctx.registerUpdate(fn), and add DOM listeners with ctx.addListener(...).
 * disposeContext() reverses all of it on unmount.
 * ======================================================================== */

import * as THREE from "three";
import GUI from "lil-gui";
import { PAGE_BG } from "./constants.js";
import { lightingFor } from "./lighting.js";

// Place the camera on its spherical orbit around `target`.
function placeCamera(camera, target, orbit) {
  camera.position.set(
    target.x + orbit.radius * Math.cos(orbit.el) * Math.sin(orbit.az),
    target.y + orbit.radius * Math.sin(orbit.el),
    target.z + orbit.radius * Math.cos(orbit.el) * Math.cos(orbit.az)
  );
  camera.lookAt(target);
}

// Three.js cameras take a VERTICAL fov, but our viewports differ wildly in shape
// (wide-short dashboard band ≈ 6:1, mobile hero ≈ 2:1, square-ish debug page). A
// fixed vertical fov makes the wide band reveal the whole world. So we hold the
// HORIZONTAL fov constant and derive vertical from the live aspect — framing the
// garden by width stays consistent everywhere; taller viewports just show more
// ground/sky. tan(h/2) = tan(v/2) · aspect  ⟹  v = 2·atan(tan(h/2) / aspect).
// Past this the derived vertical fov turns into a fisheye (a full-screen phone
// at 0.46 aspect would get 125°). Only tall viewports hit it — the band (22°),
// desktop (67°) and 2:1 mobile hero (48°) are untouched — and on those the
// scene crops at the sides like a cover-fit image instead of warping.
const MAX_V_FOV = 75;

function vFovForAspect(hFovDeg, aspect) {
  const h = THREE.MathUtils.degToRad(hFovDeg);
  const v = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(h / 2) / aspect));
  return Math.min(v, MAX_V_FOV);
}

export function createContext(root, data) {
  const positions = (data && data.positions) || [];
  const period = (data && data.period) || "afternoon";

  const width = root.clientWidth || root.offsetWidth || 800;
  const height = root.clientHeight || 380;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(PAGE_BG);

  // Slightly elevated three-quarter view: tilted down at the bed like you're
  // tending it, but shallow enough that the horizon — and the sun/moon in the
  // sky above it — stay in frame. Drag to orbit (interaction layer), so you can
  // swing up to look at the sky.
  // H_FOV is the horizontal field of view we hold constant; the camera's vertical
  // fov is derived from it + the current aspect (see vFovForAspect / ctx.applyFov),
  // so the framing survives the band ↔ mobile ↔ debug aspect swings. Tune H_FOV on
  // /garden with the "h-fov" slider, then "copy position".
  const H_FOV = 83;
  const camera = new THREE.PerspectiveCamera(
    vFovForAspect(H_FOV, width / height),
    width / height,
    0.1,
    100
  );
  camera.userData.hFov = H_FOV; // source of truth; vertical fov is derived
  // Default framing — captured in the /garden inspector ("copy position"). Frames
  // the slot cluster (see PLANT_SLOTS) at a low three-quarter angle.
  const target = new THREE.Vector3(2.921, 1.871, -2.734);
  // Spherical orbit around `target` (azimuth, elevation, radius).
  const orbit = { az: 0.582, el: 0.216, radius: 16.963, dragging: false };
  placeCamera(camera, target, orbit);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(width, height);
  renderer.setClearColor(PAGE_BG, 1); // belt-and-suspenders with scene.background
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  // Modern three colour pipeline. sRGB output is the default since r152 but we
  // set it explicitly. NoToneMapping (also the default) keeps the off-white
  // PAGE_BG landing on its exact hex so the canvas blends into the page; once
  // post-processing lands (Phase C) we can revisit ACESFilmic + an OutputPass.
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NoToneMapping;

  const canvas = renderer.domElement;
  canvas.className = "garden-canvas";
  root.appendChild(canvas);

  const ctx = {
    root,
    canvas,
    renderer,
    scene,
    camera,
    clock: new THREE.Clock(),
    size: { w: width, h: height },
    // Mutable shared state any layer may read/write.
    state: {
      period,
      positions,
      slots: (data && data.slots) || null, // optional override of PLANT_SLOTS
      orbit,
      target,
      lit: lightingFor(period), // light + sun/moon palette, computed once
      transformDragging: false, // editor sets this; interaction reads it
    },
    plants: [], // populated by the plants layer; interaction/editor read it
    layers: [],
    controls: null, // set by the inspect layer (OrbitControls); editor reads it
    composer: null, // set in Phase C (post-processing)
    gui: null, // single shared lil-gui panel; layers add folders via getGUI()
    alive: true, // flipped false in disposeContext; async layer work checks it
    _updates: [], // per-frame callbacks (t, ctx)
    _listeners: [], // [target, type, fn] for removal on teardown

    registerUpdate(fn) {
      this._updates.push(fn);
    },
    addListener(target, type, fn) {
      target.addEventListener(type, fn);
      this._listeners.push([target, type, fn]);
    },
    // Lazily create ONE shared debug panel; every debug layer adds a folder to
    // it (avoids stacked, overlapping lil-gui instances). Destroyed in teardown.
    getGUI() {
      if (!this.gui) this.gui = new GUI({ title: "garden · debug" });
      return this.gui;
    },
    // Re-derive the vertical fov from the held horizontal fov + current aspect.
    // Called on every resize and by the debug "h-fov" slider.
    applyFov() {
      this.camera.fov = vFovForAspect(this.camera.userData.hFov, this.camera.aspect);
      this.camera.updateProjectionMatrix();
    },
  };

  // Central resize: keep the camera aspect, renderer, and (later) composer in
  // sync with the #garden-root band as the dashboard reflows.
  function onResize() {
    const w = root.clientWidth || width;
    const h = root.clientHeight || height;
    ctx.size.w = w;
    ctx.size.h = h;
    camera.aspect = w / h;
    ctx.applyFov(); // re-derive vertical fov for the new aspect (+ updates projection)
    renderer.setSize(w, h);
    if (ctx.composer) ctx.composer.setSize(w, h);
  }
  ctx.addListener(window, "resize", onResize);

  return ctx;
}

export function disposeContext(ctx) {
  ctx.alive = false;

  // Drop the shared debug panel (if any layer created one).
  if (ctx.gui) {
    try {
      ctx.gui.destroy();
    } catch (e) {
      /* already gone */
    }
    ctx.gui = null;
  }

  // Drop every DOM listener (central + layer-registered).
  for (const [target, type, fn] of ctx._listeners) {
    target.removeEventListener(type, fn);
  }

  // Dispose all geometry/materials still in the scene.
  ctx.scene.traverse(function (obj) {
    if (obj.geometry) obj.geometry.dispose();
    if (obj.material) {
      (Array.isArray(obj.material) ? obj.material : [obj.material]).forEach(
        function (m) {
          m.dispose();
        }
      );
    }
  });

  if (ctx.composer && ctx.composer.dispose) ctx.composer.dispose();

  ctx.renderer.dispose();
  if (ctx.canvas && ctx.canvas.parentNode) {
    ctx.canvas.parentNode.removeChild(ctx.canvas);
  }
}
