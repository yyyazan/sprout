/* ===========================================================================
 * plants.js — one VOX potted plant per portfolio position, in a row.
 *
 * The Plants.vox parse is cached at MODULE scope (not on ctx), so SPA-navigation
 * remounts reuse it instead of re-fetching/re-parsing. Each plant is wrapped in
 * a holder Group (carries position data + a rest Y) so later phases can
 * raycast / hover / lift the whole plant cleanly.
 * ======================================================================== */

import * as THREE from "three";
import { VOXLoader, VOXMesh } from "three/addons/loaders/VOXLoader.js";
import {
  GOOD_PLANT_MODELS,
  PLANT_SCALE,
  PLANT_SLOTS,
  ALLOC_SCALE,
} from "../constants.js";

// Module-level cache: parse Plants.vox ONCE, reuse across scene rebuilds.
// Queued callbacks fire when ready. Never disposed — survives remounts.
let _voxChunks = null;
let _voxLoading = false;
let _voxWaiters = [];

function withVoxChunks(cb) {
  if (_voxChunks) {
    cb(_voxChunks);
    return;
  }
  _voxWaiters.push(cb);
  if (_voxLoading) return;
  _voxLoading = true;
  new VOXLoader().load(
    "/Plants.vox",
    function (result) {
      // Modern VOXLoader returns { chunks, scene } (r128 returned a bare array;
      // a deprecation Proxy still allows array access). Use .chunks.
      const chunks = (result && result.chunks) || result;

      // Defensive palette fix (was REQUIRED on r128): the r128 loader assigned
      // the file's single RGBA palette only to the LAST model, leaving the
      // others on DEFAULT_PALETTE (alien colours). Modern three (r155+) already
      // broadcasts the palette to every chunk, so this is now a no-op UNLESS
      // chunks disagree — only then do we rebroadcast the longest palette.
      const lens = chunks.map((c) => (c.palette ? c.palette.length : 0));
      const allSame = lens.every((l) => l === lens[0]);
      if (!allSame) {
        let real = null;
        for (let k = 0; k < chunks.length; k++) {
          if (chunks[k].palette && chunks[k].palette.length > 256) {
            real = chunks[k].palette;
            break;
          }
        }
        if (real) chunks.forEach((ch) => (ch.palette = real));
      }

      _voxChunks = chunks;
      _voxLoading = false;
      const ws = _voxWaiters;
      _voxWaiters = [];
      ws.forEach((w) => w(chunks));
    },
    undefined,
    function (err) {
      _voxLoading = false;
      console.error("[garden] VOXLoader failed:", err);
    }
  );
}

// Deterministic ticker → model index. Same ticker always grows the same plant
// (stable across reloads); the holdings look varied. Pure function of the
// ticker string — no randomness, no recompute.
function plantModelFor(ticker) {
  const s = String(ticker || "");
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return GOOD_PLANT_MODELS[h % GOOD_PLANT_MODELS.length];
}

// Build ONE plant for a position. This is the single swap point for future
// per-model .glb files: replace the VOXMesh body with a gltfLoader.load(...)
// returning a Group seated the same way; nothing else changes.
function loadPlant(position, chunks) {
  const idx = Math.min(plantModelFor(position.ticker), chunks.length - 1);
  const mesh = new VOXMesh(chunks[idx]);
  mesh.scale.setScalar(PLANT_SCALE);
  mesh.updateMatrixWorld(true);
  // Seat base on the bed (y=0) and centre on its own origin.
  const box = new THREE.Box3().setFromObject(mesh);
  mesh.position.x -= (box.min.x + box.max.x) / 2;
  mesh.position.z -= (box.min.z + box.max.z) / 2;
  mesh.position.y -= box.min.y;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

// Allocation (position_pct, 0–100) → holder scale multiplier. Relative to the
// largest holding in the current set so the biggest plant is always ALLOC_SCALE[1]
// and the rest scale down from there; sqrt lifts small holdings off the floor so
// they stay visible rather than shrinking to nothing.
function allocScaler(positions) {
  const maxW = Math.max(0.0001, ...positions.map((p) => +p.position_pct || 0));
  return function (pos) {
    const t = Math.sqrt(Math.min(1, (+pos.position_pct || 0) / maxW));
    return ALLOC_SCALE[0] + t * (ALLOC_SCALE[1] - ALLOC_SCALE[0]);
  };
}

export default function createPlants() {
  return {
    name: "plants",
    build(ctx) {
      const positions = ctx.state.positions;
      if (!positions || !positions.length) return;
      withVoxChunks(function (chunks) {
        if (!ctx.alive) return; // unmounted while the VOX parse was in flight
        if (!chunks || !chunks.length) return;

        // Biggest allocation first → fills the prime front-centre slots in order.
        const sorted = [...positions].sort(
          (a, b) => (+b.position_pct || 0) - (+a.position_pct || 0)
        );
        const scaleFor = allocScaler(sorted);
        // A host may supply its own arrangement (the sign-in screen composes
        // around a centred card); the dashboard bed uses the tuned defaults.
        const slots = ctx.state.slots || PLANT_SLOTS;
        if (sorted.length > slots.length) {
          console.warn(
            `[garden] ${sorted.length} holdings but only ${slots.length} slots — ` +
              "wrapping (overlaps possible). Add more PLANT_SLOTS."
          );
        }

        for (let i = 0; i < sorted.length; i++) {
          const slot = slots[i % slots.length];
          const holder = new THREE.Group();
          holder.add(loadPlant(sorted[i], chunks));
          // slot.y lets a host raise or sink a plant (bare scenes have no ground)
          holder.position.set(slot.x, slot.y || 0, slot.z);
          holder.rotation.y = slot.rot || 0;
          holder.scale.setScalar(scaleFor(sorted[i]));
          holder.name = "plant";
          holder.userData.position = sorted[i]; // for hover/click later
          holder.userData.slotIndex = i; // editor reads this for "Copy PLANT_SLOTS"
          holder.userData.baseY = slot.y || 0;
          ctx.scene.add(holder);
          ctx.plants.push(holder);
        }
      });
    },
  };
}
