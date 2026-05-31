/* ===========================================================================
 * garden.js — Sprout garden view (Three.js r128)
 *
 * One plant per portfolio position, growing straight out of the page. Dash
 * hands over position data once via the #garden-data store (window.initGarden);
 * after that, everything — scene, plants, hover, particles, detail overlay —
 * lives here. Dash never touches the canvas again.
 *
 * Build phases (see plan):
 *   Phase 2  scene: page-matched bg, bed, lights, sun/moon, drag-to-orbit cam  ✓
 *   Phase 3  plants: one VOX potted plant per position, in a row on the bed    ✓
 *   Phase 4  interaction: raycaster hover-glow, burstParticles(), detail card  ← next
 *
 * r128 constraints: no OrbitControls (manual camera only), no CapsuleGeometry
 * (Cylinder/Sphere/Box only).
 * ======================================================================== */

(function () {
  "use strict";

  // Must match --bg in app.css so the canvas has no visible edge — the plants
  // look like they grow straight out of the page, not out of a framed box.
  var PAGE_BG = 0xf7f6f5;

  // Single module-level scene state. Rebuilt on each init so Dash page
  // navigation (which recreates #garden-root) never leaves a stale canvas or a
  // runaway animation frame behind.
  var G = null;

  // -------------------------------------------------------------------------
  // Entry point — called by the clientside callback whenever #garden-data is
  // populated (and on navigation). Idempotent: tears down any prior scene.
  // -------------------------------------------------------------------------
  window.initGarden = function (data) {
    if (typeof THREE === "undefined") return; // CDN not ready / failed
    var root = document.getElementById("garden-root");
    if (!root) return;

    teardown();

    var positions = (data && data.positions) || [];
    var period = (data && data.period) || "afternoon";

    G = buildScene(root, period);
    G.positions = positions;

    buildPlants(G, positions); // one potted plant per holding, in a row

    // Phase 4: setupInteraction(G);

    animate();
  };

  // -------------------------------------------------------------------------
  // Scene construction
  // -------------------------------------------------------------------------
  function buildScene(root, period) {
    var width = root.clientWidth || root.offsetWidth || 800;
    var height = root.clientHeight || 380;

    var scene = new THREE.Scene();
    scene.background = new THREE.Color(PAGE_BG);

    // Slightly elevated three-quarter view: tilted down at the bed like you're
    // tending it, but shallow enough that the horizon — and the sun/moon in the
    // sky above it — stay in frame. Drag to orbit (manual; r128 has no
    // OrbitControls), so you can swing up to look at the sky.
    var camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
    var target = new THREE.Vector3(0, 1.2, 0);
    // Spherical orbit around `target` (azimuth, elevation, radius). Pulled back
    // far enough to frame a full row of plants across the bed.
    var orbit = { az: 0, el: 0.24, radius: 16, dragging: false };
    camera.position.set(
      target.x + orbit.radius * Math.cos(orbit.el) * Math.sin(orbit.az),
      target.y + orbit.radius * Math.sin(orbit.el),
      target.z + orbit.radius * Math.cos(orbit.el) * Math.cos(orbit.az)
    );
    camera.lookAt(target);

    var renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height);
    renderer.setClearColor(PAGE_BG, 1); // belt-and-suspenders with scene.background
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    var canvas = renderer.domElement;
    canvas.className = "garden-canvas";
    root.appendChild(canvas);

    // ── Lights ────────────────────────────────────────────────────────────
    // Gentle warm ambient + one directional key. Tone shifts with time of day.
    var lit = lightingFor(period);
    var ambient = new THREE.AmbientLight(lit.ambientColor, lit.ambientIntensity);
    scene.add(ambient);

    var key = new THREE.DirectionalLight(lit.keyColor, lit.keyIntensity);
    key.position.copy(lit.keyPos);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    key.shadow.camera.near = 1;
    key.shadow.camera.far = 40;
    key.shadow.camera.left = -10;
    key.shadow.camera.right = 10;
    key.shadow.camera.top = 10;
    key.shadow.camera.bottom = -10;
    key.shadow.radius = 4; // soft edges
    scene.add(key);

    // ── Garden bed ────────────────────────────────────────────────────────
    var bedGeo = new THREE.PlaneGeometry(40, 16);
    var bedMat = new THREE.MeshStandardMaterial({
      color: 0xb8c294, // soft sage soil — distinct from the page bg, still gentle
      roughness: 0.95,
      metalness: 0.0,
    });
    var bed = new THREE.Mesh(bedGeo, bedMat);
    bed.rotation.x = -Math.PI / 2;
    bed.position.y = 0;
    bed.receiveShadow = true;
    scene.add(bed);

    // ── Sun / moon ────────────────────────────────────────────────────────
    var sky = buildSunMoon(period, lit.keyPos);
    scene.add(sky);

    // ── Drag-to-orbit ─────────────────────────────────────────────────────
    // Drag left/right to spin around the bed; drag up to tilt toward the sky
    // (find the sun), drag down for a more top-down tending view. Elevation is
    // clamped so you never flip under the ground or fully overhead.
    canvas.style.cursor = "grab";
    var last = { x: 0, y: 0 };
    function onDown(e) {
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
      if (!orbit.dragging) return;
      orbit.az += (e.clientX - last.x) * 0.005;
      orbit.el = Math.max(0.04, Math.min(0.95, orbit.el + (e.clientY - last.y) * 0.005));
      last.x = e.clientX;
      last.y = e.clientY;
    }
    canvas.addEventListener("mousedown", onDown);
    window.addEventListener("mouseup", onUp);
    canvas.addEventListener("mousemove", onMove);

    function onResize() {
      var w = root.clientWidth || width;
      var h = root.clientHeight || height;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    }
    window.addEventListener("resize", onResize);

    return {
      root: root,
      canvas: canvas,
      scene: scene,
      camera: camera,
      target: target,
      orbit: orbit,
      renderer: renderer,
      plants: [],
      raf: 0,
      t0: performance.now(),
      _listeners: [
        [canvas, "mousedown", onDown],
        [window, "mouseup", onUp],
        [canvas, "mousemove", onMove],
        [window, "resize", onResize],
      ],
    };
  }

  // Warm key light + ambient tuned per time of day. keyPos doubles as the
  // sun/moon position so light and object always agree.
  function lightingFor(period) {
    // keyPos sits in the sky behind the bed (negative z) at a modest height so
    // the sun/moon orb stays in frame; ambient is kept moderate so the bed and
    // pots keep their colour without washing out, while shadows stay readable.
    switch (period) {
      case "morning":
        return {
          ambientColor: 0xfff1e0, ambientIntensity: 0.55,
          keyColor: 0xffe8c2, keyIntensity: 0.9,
          keyPos: new THREE.Vector3(-6, 3.0, -9),
        };
      case "afternoon":
        return {
          ambientColor: 0xfff6ec, ambientIntensity: 0.6,
          keyColor: 0xfff3d6, keyIntensity: 1.0,
          keyPos: new THREE.Vector3(3, 3.4, -9),
        };
      case "evening":
        return {
          ambientColor: 0xffe4cf, ambientIntensity: 0.5,
          keyColor: 0xffb074, keyIntensity: 0.95, // warm sunset
          keyPos: new THREE.Vector3(7, 2.6, -9),
        };
      default: // night
        return {
          ambientColor: 0xdfe6f2, ambientIntensity: 0.4,
          keyColor: 0xbcc8e6, keyIntensity: 0.55, // cool moonlight
          keyPos: new THREE.Vector3(-5, 3.2, -9),
        };
    }
  }

  // A glowing orb standing in for the sun or moon, placed at the key-light
  // position. Colours are saturated (not pale) so it reads clearly against the
  // off-white sky, with a soft larger halo for a gentle bloom. Placeholder —
  // the real sun/moon becomes a proper Three.js object later.
  function buildSunMoon(period, pos) {
    var isNight = period === "night";
    // Saturated enough to stand out on #f7f6f5 (pale yellow vanished).
    var color =
      isNight ? 0x8e9bc4 : period === "evening" ? 0xef6b3a : 0xf6a826;
    var group = new THREE.Group();

    // Unlit basic material so the disc shows its true saturated colour no
    // matter how the scene is lit — an emissive Standard mat was blowing out.
    var core = new THREE.Mesh(
      new THREE.SphereGeometry(isNight ? 1.0 : 1.3, 28, 28),
      new THREE.MeshBasicMaterial({ color: color })
    );
    group.add(core);

    // Soft halo: a larger translucent shell for a faint aura. Normal blending
    // (not additive — additive washes out to white on a light background).
    var halo = new THREE.Mesh(
      new THREE.SphereGeometry(isNight ? 1.7 : 2.2, 28, 28),
      new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: 0.16,
        depthWrite: false,
      })
    );
    group.add(halo);

    group.position.copy(pos);
    group.name = "sun-moon";
    return group;
  }

  // -------------------------------------------------------------------------
  // Plants — one potted plant per position, in a row on the bed.
  // -------------------------------------------------------------------------

  // Curated subset of Plants.vox (audited): the 19 models that are complete
  // potted plants. Excluded — 7–11 (empty pot holders/stands) and 24–28 (bare
  // plants with no pot).
  var GOOD_PLANT_MODELS = [
    0, 1, 2, 3, 4, 5, 6, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23,
  ];
  var PLANT_SCALE = 0.13;
  var PLANT_SPACING = 2.6; // x-distance between plants in the row

  // Module-level cache: parse Plants.vox ONCE, reuse across scene rebuilds
  // (navigation re-runs initGarden). Queued callbacks fire when ready.
  var _voxChunks = null;
  var _voxLoading = false;
  var _voxWaiters = [];

  function withVoxChunks(cb) {
    if (_voxChunks) { cb(_voxChunks); return; }
    _voxWaiters.push(cb);
    if (_voxLoading) return;
    if (typeof THREE.VOXLoader === "undefined") {
      console.warn("[garden] VOXLoader unavailable — no plants");
      return;
    }
    _voxLoading = true;
    new THREE.VOXLoader().load(
      "/Plants.vox",
      function (chunks) {
        // VOXLoader (r128) bug: the global RGBA palette chunk comes AFTER all
        // the models in the file, so the loader only assigns it to the LAST
        // model — every other model keeps DEFAULT_PALETTE (the alien colours).
        // The .vox already holds the artist's true palette (green stems, etc.);
        // find it (the one longer than the 256-entry default) and apply it to
        // every chunk so all models render with the intended colours.
        var real = null;
        for (var k = 0; k < chunks.length; k++) {
          if (chunks[k].palette && chunks[k].palette.length > 256) {
            real = chunks[k].palette;
            break;
          }
        }
        if (real) chunks.forEach(function (ch) { ch.palette = real; });
        _voxChunks = chunks;
        _voxLoading = false;
        var ws = _voxWaiters;
        _voxWaiters = [];
        ws.forEach(function (w) { w(chunks); });
      },
      undefined,
      function (err) {
        _voxLoading = false;
        console.error("[garden] VOXLoader failed:", err);
      }
    );
  }

  // Deterministic ticker → model index. Same ticker always grows the same
  // plant (stable across reloads); the holdings look varied. Pure function of
  // the ticker string — no randomness, no recompute.
  function plantModelFor(ticker) {
    var s = String(ticker || "");
    var h = 0;
    for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
    return GOOD_PLANT_MODELS[h % GOOD_PLANT_MODELS.length];
  }

  // Build ONE plant for a position. This is the single swap point for future
  // per-model .glb files: replace the VOXMesh body with
  //   gltfLoader.load('/assets/models/' + name + '.glb', cb)
  // returning a Group seated the same way; nothing else changes.
  // (Path B note: we're effectively already on the voxel path — VOXMesh builds
  // the model from the .vox; if we later want per-voxel particle emission we'd
  // swap VOXMesh for an InstancedMesh of cubes built from chunk.data.)
  function loadPlant(position, chunks) {
    var idx = Math.min(plantModelFor(position.ticker), chunks.length - 1);
    var mesh = new THREE.VOXMesh(chunks[idx]);
    mesh.scale.setScalar(PLANT_SCALE);
    mesh.updateMatrixWorld(true);
    // Seat base on the bed (y=0) and centre on its own origin.
    var box = new THREE.Box3().setFromObject(mesh);
    mesh.position.x -= (box.min.x + box.max.x) / 2;
    mesh.position.z -= (box.min.z + box.max.z) / 2;
    mesh.position.y -= box.min.y;
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    return mesh;
  }

  // Lay one plant per position, evenly spaced in a row across the bed. Each is
  // wrapped in a holder Group (carries the position data + a rest Y) so Phase 4
  // can raycast/hover/lift the whole plant cleanly.
  function buildPlants(g, positions) {
    if (!positions || !positions.length) return;
    withVoxChunks(function (chunks) {
      if (!chunks || !chunks.length) return;
      var n = positions.length;
      var totalW = (n - 1) * PLANT_SPACING;
      for (var i = 0; i < n; i++) {
        var holder = new THREE.Group();
        holder.add(loadPlant(positions[i], chunks));
        holder.position.set(-totalW / 2 + i * PLANT_SPACING, 0, 0);
        holder.name = "plant";
        holder.userData.position = positions[i]; // for Phase 4 hover/click
        holder.userData.baseY = 0;
        g.scene.add(holder);
        g.plants.push(holder);
      }
    });
  }

  // -------------------------------------------------------------------------
  // Animation loop — spherical orbit with a gentle idle sway for life.
  // -------------------------------------------------------------------------
  function animate() {
    if (!G) return;
    G.raf = requestAnimationFrame(animate);

    var t = (performance.now() - G.t0) / 1000;

    // Spherical orbit. Idle → a tiny azimuth sway keeps the scene alive; while
    // dragging → follow the user exactly. Lerp so motion never snaps.
    var o = G.orbit;
    var az = o.az + (o.dragging ? 0 : Math.sin(t * 0.22) * 0.04);
    var r = o.radius;
    var dx = G.target.x + r * Math.cos(o.el) * Math.sin(az);
    var dy = G.target.y + r * Math.sin(o.el);
    var dz = G.target.z + r * Math.cos(o.el) * Math.cos(az);
    G.camera.position.x += (dx - G.camera.position.x) * 0.08;
    G.camera.position.y += (dy - G.camera.position.y) * 0.08;
    G.camera.position.z += (dz - G.camera.position.z) * 0.08;
    G.camera.lookAt(G.target);

    // Phase 4: hover lerp / particle updates go here.

    G.renderer.render(G.scene, G.camera);
  }

  // -------------------------------------------------------------------------
  // Teardown — cancel the frame, drop listeners, dispose GL, clear the canvas.
  // -------------------------------------------------------------------------
  function teardown() {
    if (!G) return;
    if (G.raf) cancelAnimationFrame(G.raf);
    (G._listeners || []).forEach(function (l) {
      l[0].removeEventListener(l[1], l[2]);
    });
    if (G.scene) {
      G.scene.traverse(function (obj) {
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) {
          (Array.isArray(obj.material) ? obj.material : [obj.material]).forEach(
            function (m) { m.dispose(); }
          );
        }
      });
    }
    if (G.renderer) {
      G.renderer.dispose();
      if (G.canvas && G.canvas.parentNode) {
        G.canvas.parentNode.removeChild(G.canvas);
      }
    }
    G = null;
  }

  // Exposed so the SvelteKit GardenView can tear the scene down on unmount
  // (SPA navigation), preventing a leaked rAF loop / orphaned canvas.
  window.gardenTeardown = teardown;
})();
