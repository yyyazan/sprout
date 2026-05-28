/* Card hand — layout, hover pop/tilt, and a WebGL holographic foil.
 *
 * window.initCardHand() is fired once on page load by a clientside callback in
 * the Dashboard page (and again on navigation). It lays the cards out in a
 * straight, uniformly-overlapping row and binds the handlers. Layout also
 * re-runs on window resize.
 *
 * Events bind to the `.portfolio-card` wrapper, which NEVER transforms, so its
 * hit area is stable (no hover jitter). The transform (pop/tilt/scale) goes on
 * the inner `.card-inner` face.
 *
 * The holo is a direct WebGL port of the Balatro "Holographic" canvas_item
 * shader. A single shared <canvas> is moved into the hovered card's
 * `.card-inner` and animated; being a child, it pops/tilts with the card. */

(function () {
  var CARD_W = 148;
  var TILT_X = 13; // deg
  var TILT_Y = 14; // deg
  var POP = 74; // px

  function clamp(v) { return v < -1 ? -1 : v > 1 ? 1 : v; }

  function layout() {
    var hand = document.getElementById("card-hand");
    if (!hand) return;
    var cards = hand.querySelectorAll(".portfolio-card");
    var n = cards.length;
    if (!n) return;

    var containerW = hand.clientWidth;
    var spacing = n > 1
      ? Math.max(34, Math.min(88, (containerW - CARD_W) / (n - 1)))
      : 0;
    var rowW = CARD_W + spacing * (n - 1);
    var offset = Math.max(0, (containerW - rowW) / 2);

    cards.forEach(function (card, i) {
      card.style.left = offset + i * spacing + "px";
      if (card.dataset.popped !== "1") card.style.zIndex = String(10 + i);
    });
  }

  /* ───────────────────────── WebGL holo (Balatro port) ───────────────── */
  var Holo = (function () {
    var VERT =
      "attribute vec2 a_pos; varying vec2 v_uv;" +
      "void main(){ v_uv = a_pos * 0.5 + 0.5; gl_Position = vec4(a_pos, 0.0, 1.0); }";

    // Ported from the Godot canvas_item shader. Input "texel" is white (we use
    // the shader as a standalone overlay), so delta is constant and the output
    // is the pure holographic interference, alpha-faded per the original.
    var FRAG =
      "precision highp float;" +
      "uniform vec2 u_offset; uniform float u_speed; uniform float u_time;" +
      "varying vec2 v_uv;" +
      "void main(){" +
      "  vec2 uv = v_uv;" +
      "  vec4 texel = vec4(1.0);" +
      "  vec2 a = uv - vec2(0.5);" +
      "  float low = min(texel.r, min(texel.g, texel.b));" +
      "  float high = max(texel.r, max(texel.g, texel.b));" +
      "  float delta = min(high, max(0.5, 1.0 - low));" +
      "  vec2 foil = vec2(u_time * u_speed + u_offset.x, u_offset.y);" +
      "  float fac = max(min(2.0*sin((length(90.0*a)+foil.x*2.0)+3.0*(1.0+0.8*cos(length(113.1121*a)-foil.x*3.121)))-1.0-max(5.0-length(90.0*a),0.0),1.0),0.0);" +
      "  vec2 rotater = vec2(cos(foil.x*0.1221), sin(foil.x*0.3512));" +
      "  float angle = dot(rotater, a)/(length(rotater)*length(a)+1e-4);" +
      "  float fac2 = max(min(5.0*cos(foil.y*0.3+angle*3.14*(2.2+0.9*sin(foil.x*1.65+0.2*foil.y)))-4.0-max(2.0-length(20.0*a),0.0),1.0),0.0);" +
      "  float fac3 = 0.3*max(min(2.0*sin(foil.x*5.0+uv.x*3.0+3.0*(1.0+0.5*cos(foil.x*7.0)))-1.0,1.0),-1.0);" +
      "  float fac4 = 0.3*max(min(2.0*sin(foil.x*6.66+uv.y*3.8+3.0*(1.0+0.5*cos(foil.x*3.414)))-1.0,1.0),-1.0);" +
      "  float maxfac = max(max(fac,max(fac2,max(fac3,max(fac4,0.0))))+2.2*(fac+fac2+fac3+fac4),0.0);" +
      "  vec4 o = texel;" +
      "  o.r = texel.r - delta + delta*maxfac*0.3;" +
      "  o.g = texel.g - delta + delta*maxfac*0.3;" +
      "  o.b = texel.b + delta*maxfac*1.9;" +
      "  o.a = min(texel.a, 0.3*texel.a + 0.9*min(0.5, maxfac*0.1));" +
      "  gl_FragColor = o;" +
      "}";

    var canvas, gl, uOffset, uSpeed, uTime, raf = 0;
    var activeInner = null, startT = 0, ox = 0, oy = 0, ready = false, failed = false;

    function compile(type, src) {
      var s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      return s;
    }

    function init() {
      if (ready) return true;
      if (failed) return false;
      canvas = document.createElement("canvas");
      canvas.className = "holo-canvas";
      gl = canvas.getContext("webgl", { alpha: true, premultipliedAlpha: false, antialias: true });
      if (!gl) { failed = true; return false; }
      var prog = gl.createProgram();
      gl.attachShader(prog, compile(gl.VERTEX_SHADER, VERT));
      gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, FRAG));
      gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) { failed = true; return false; }
      gl.useProgram(prog);
      var buf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
      var loc = gl.getAttribLocation(prog, "a_pos");
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
      uOffset = gl.getUniformLocation(prog, "u_offset");
      uSpeed = gl.getUniformLocation(prog, "u_speed");
      uTime = gl.getUniformLocation(prog, "u_time");
      gl.uniform1f(uSpeed, 1.0);
      ready = true;
      return true;
    }

    function size() {
      if (!activeInner) return;
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      var w = Math.round(activeInner.offsetWidth * dpr);
      var h = Math.round(activeInner.offsetHeight * dpr);
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w; canvas.height = h;
        gl.viewport(0, 0, w, h);
      }
    }

    function frame(now) {
      if (!activeInner) return;
      size();
      gl.uniform2f(uOffset, ox, oy);
      gl.uniform1f(uTime, (now - startT) / 1000);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      raf = window.requestAnimationFrame(frame);
    }

    return {
      attach: function (inner) {
        if (!init()) return;
        activeInner = inner;
        inner.appendChild(canvas);
        startT = (window.performance && performance.now()) || 0;
        size();
        // force reflow so the opacity transition runs
        void canvas.offsetWidth;
        canvas.classList.add("is-on");
        if (!raf) raf = window.requestAnimationFrame(frame);
      },
      setOffset: function (px, py) { ox = px * 3.2; oy = py * 3.2; },
      detach: function (inner) {
        if (activeInner !== inner) return; // a newer card already took over
        activeInner = null;
        if (raf) { window.cancelAnimationFrame(raf); raf = 0; }
        if (canvas) { canvas.classList.remove("is-on"); if (canvas.parentNode) canvas.parentNode.removeChild(canvas); }
      },
    };
  })();

  function bind(card) {
    if (card.dataset.bound === "1") return;
    card.dataset.bound = "1";
    var inner = card.querySelector(".card-inner");

    card.addEventListener("mouseenter", function () {
      if (inner) inner.style.transition = "none";
      card.style.zIndex = "400";
      card.dataset.popped = "1";
      if (inner) Holo.attach(inner);
    });

    card.addEventListener("mousemove", function (e) {
      // Wrapper never transforms → its rect is stable frame-to-frame.
      var r = card.getBoundingClientRect();
      var px = clamp(((e.clientX - r.left) / r.width) * 2 - 1);  // -1..1
      var py = clamp(((e.clientY - r.top) / r.height) * 2 - 1);
      if (inner) {
        inner.style.transform =
          "translateY(-" + POP + "px) scale(1.08) perspective(700px) " +
          "rotateX(" + (-py * TILT_X).toFixed(2) + "deg) " +
          "rotateY(" + (px * TILT_Y).toFixed(2) + "deg)";
      }
      Holo.setOffset(px, py);
    });

    card.addEventListener("mouseleave", function () {
      if (inner) {
        inner.style.transition = "transform .38s cubic-bezier(.34, 1.56, .64, 1)";
        inner.style.transform = "none";
        Holo.detach(inner);
      }
      card.dataset.popped = "0";
      var idx = parseInt(card.getAttribute("data-index") || "0", 10);
      window.setTimeout(function () {
        if (card.dataset.popped !== "1") card.style.zIndex = String(10 + idx);
      }, 380);
    });
  }

  // Hide logos that fail to load so the two-letter fallback (sitting behind)
  // shows cleanly instead of a broken-image glyph.
  function wireLogo(img) {
    if (img.dataset.wired === "1") return;
    img.dataset.wired = "1";
    var hide = function () { img.style.display = "none"; };
    img.addEventListener("error", hide);
    if (img.complete && img.naturalWidth === 0) hide();
  }

  window.initCardHand = function () {
    var hand = document.getElementById("card-hand");
    if (!hand) return;
    hand.querySelectorAll(".portfolio-card").forEach(bind);
    hand.querySelectorAll(".card-logo").forEach(wireLogo);
    layout();
  };

  if (!window.__cardHandResize) {
    window.__cardHandResize = true;
    window.addEventListener("resize", layout);
    window.addEventListener("load", window.initCardHand);
  }
})();
