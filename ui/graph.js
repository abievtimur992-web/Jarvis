/*
 * graph.js — kúsh-baylanıslı (force-directed) grafik, Canvas penen.
 *
 * SVG emes, Canvas qollanıladı (kóp jazba bolsa tezirek isleydi). Repulsiya
 * ushın spatial grid + distance cutoff bar — hár bir jazbanı hámmesi menen
 * salıstırmaw ushın (bul aste isleytuǵın edi).
 */

(function () {
  "use strict";

  const TYPE_COLORS = {
    brendler: "#4d6cf0",
    klientler: "#e8722c",
    kundelik: "#3fb27f",
    jazba: "#c9cdd6",
    qosımsha: "#a78bfa",
    _default: "#8b909c",
  };

  function colorForType(type) {
    return TYPE_COLORS[type] || TYPE_COLORS._default;
  }

  class ForceGraph {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.nodes = [];
      this.edges = [];
      this.nodeById = new Map();
      this.adjacency = new Map();

      this.camera = { x: 0, y: 0, zoom: 1 };
      this.dragging = null;
      this.panStart = null;
      this.mouse = { screenX: 0, screenY: 0 };
      this.hoveredNode = null;
      this.focusedNode = null;
      this.highlightPath = new Set();

      this.activeTypes = null; // null = bári kórinedi
      this.lastInteraction = performance.now();
      this.idlePulse = null;

      this.onHover = null;
      this.onClick = null;
      this.onShiftClick = null;

      this._resize();
      window.addEventListener("resize", () => this._resize());
      this._bindEvents();
      requestAnimationFrame(this._tick.bind(this));
    }

    _resize() {
      const dpr = window.devicePixelRatio || 1;
      this.width = window.innerWidth;
      this.height = window.innerHeight;
      this.canvas.width = this.width * dpr;
      this.canvas.height = this.height * dpr;
      this.canvas.style.width = this.width + "px";
      this.canvas.style.height = this.height + "px";
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    setData(data) {
      const prevPositions = new Map();
      this.nodes.forEach((n) => prevPositions.set(n.id, { x: n.x, y: n.y }));

      this.nodes = data.nodes.map((n) => {
        const prev = prevPositions.get(n.id);
        return Object.assign({}, n, {
          x: prev ? prev.x : (Math.random() - 0.5) * 500,
          y: prev ? prev.y : (Math.random() - 0.5) * 500,
          vx: 0,
          vy: 0,
          radius: 6 + Math.sqrt(n.connections || 0) * 3.2,
        });
      });
      this.edges = data.edges.slice();
      this.nodeById = new Map(this.nodes.map((n) => [n.id, n]));

      this.adjacency = new Map();
      this.nodes.forEach((n) => this.adjacency.set(n.id, new Set()));
      this.edges.forEach((e) => {
        if (this.adjacency.has(e.source)) this.adjacency.get(e.source).add(e.target);
        if (this.adjacency.has(e.target)) this.adjacency.get(e.target).add(e.source);
      });
    }

    setFilter(typesOrNull) {
      this.activeTypes = typesOrNull;
    }

    focusNodeById(id) {
      const n = this.nodeById.get(id);
      if (n) this.focusedNode = n;
    }

    _bindEvents() {
      const c = this.canvas;
      c.addEventListener("mousemove", (e) => this._onMouseMove(e));
      c.addEventListener("mousedown", (e) => this._onMouseDown(e));
      window.addEventListener("mouseup", () => this._onMouseUp());
      c.addEventListener("wheel", (e) => this._onWheel(e), { passive: false });
      c.addEventListener("click", (e) => this._onClick(e));
    }

    _screenToWorld(sx, sy) {
      return {
        x: (sx - this.width / 2) / this.camera.zoom + this.camera.x,
        y: (sy - this.height / 2) / this.camera.zoom + this.camera.y,
      };
    }

    _nodeVisible(n) {
      return !this.activeTypes || this.activeTypes.has(n.type);
    }

    _nodeAtScreen(sx, sy) {
      const w = this._screenToWorld(sx, sy);
      let best = null;
      let bestDist = Infinity;
      for (const n of this.nodes) {
        if (!this._nodeVisible(n)) continue;
        const dx = n.x - w.x;
        const dy = n.y - w.y;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d <= n.radius + 4 && d < bestDist) {
          best = n;
          bestDist = d;
        }
      }
      return best;
    }

    _onMouseMove(e) {
      const rect = this.canvas.getBoundingClientRect();
      this.mouse.screenX = e.clientX - rect.left;
      this.mouse.screenY = e.clientY - rect.top;
      this.lastInteraction = performance.now();

      if (this.dragging) {
        const w = this._screenToWorld(this.mouse.screenX, this.mouse.screenY);
        this.dragging.x = w.x;
        this.dragging.y = w.y;
        this.dragging.vx = 0;
        this.dragging.vy = 0;
        return;
      }
      if (this.panStart) {
        const dx = (e.clientX - this.panStart.sx) / this.camera.zoom;
        const dy = (e.clientY - this.panStart.sy) / this.camera.zoom;
        this.camera.x = this.panStart.cx - dx;
        this.camera.y = this.panStart.cy - dy;
        return;
      }

      const hovered = this._nodeAtScreen(this.mouse.screenX, this.mouse.screenY);
      if (hovered !== this.hoveredNode) {
        this.hoveredNode = hovered;
        if (this.onHover) this.onHover(hovered);
      }
    }

    _onMouseDown(e) {
      const rect = this.canvas.getBoundingClientRect();
      const node = this._nodeAtScreen(e.clientX - rect.left, e.clientY - rect.top);
      if (node) {
        this.dragging = node;
      } else {
        this.panStart = { sx: e.clientX, sy: e.clientY, cx: this.camera.x, cy: this.camera.y };
      }
    }

    _onMouseUp() {
      this.dragging = null;
      this.panStart = null;
    }

    _onWheel(e) {
      e.preventDefault();
      const factor = e.deltaY > 0 ? 0.9 : 1.1;
      this.camera.zoom = Math.min(3, Math.max(0.25, this.camera.zoom * factor));
      this.lastInteraction = performance.now();
    }

    _onClick(e) {
      const rect = this.canvas.getBoundingClientRect();
      const node = this._nodeAtScreen(e.clientX - rect.left, e.clientY - rect.top);
      this.lastInteraction = performance.now();
      if (!node) return;

      if (e.shiftKey && this.focusedNode && this.focusedNode.id !== node.id) {
        this._highlightShortestPath(this.focusedNode.id, node.id);
        if (this.onShiftClick) this.onShiftClick(this.focusedNode, node);
        return;
      }

      this.focusedNode = node;
      this.highlightPath = new Set();
      if (this.onClick) this.onClick(node);
    }

    _highlightShortestPath(fromId, toId) {
      const prev = new Map();
      const visited = new Set([fromId]);
      const queue = [fromId];
      while (queue.length) {
        const cur = queue.shift();
        if (cur === toId) break;
        const neighbors = this.adjacency.get(cur) || new Set();
        for (const nb of neighbors) {
          if (!visited.has(nb)) {
            visited.add(nb);
            prev.set(nb, cur);
            queue.push(nb);
          }
        }
      }
      const path = [];
      if (toId === fromId || prev.has(toId)) {
        let cur = toId;
        while (cur !== undefined) {
          path.push(cur);
          if (cur === fromId) break;
          cur = prev.get(cur);
        }
      }
      this.highlightPath = new Set(path);
    }

    _step() {
      const nodes = this.nodes.filter((n) => this._nodeVisible(n));
      const CUTOFF = 220;
      const grid = new Map();
      const key = (x, y) => Math.floor(x / CUTOFF) + ":" + Math.floor(y / CUTOFF);
      nodes.forEach((n) => {
        const k = key(n.x, n.y);
        if (!grid.has(k)) grid.set(k, []);
        grid.get(k).push(n);
      });

      const REPULSION = 2600;
      for (const n of nodes) {
        let fx = 0, fy = 0;
        const cx = Math.floor(n.x / CUTOFF);
        const cy = Math.floor(n.y / CUTOFF);
        for (let gx = cx - 1; gx <= cx + 1; gx++) {
          for (let gy = cy - 1; gy <= cy + 1; gy++) {
            const bucket = grid.get(gx + ":" + gy);
            if (!bucket) continue;
            for (const other of bucket) {
              if (other === n) continue;
              const dx = n.x - other.x;
              const dy = n.y - other.y;
              let dist2 = dx * dx + dy * dy;
              if (dist2 < 1) dist2 = 1;
              const dist = Math.sqrt(dist2);
              if (dist > CUTOFF) continue;
              const force = REPULSION / dist2;
              fx += (dx / dist) * force;
              fy += (dy / dist) * force;
            }
          }
        }
        fx += -n.x * 0.006;
        fy += -n.y * 0.006;
        n.fx = fx;
        n.fy = fy;
      }

      const SPRING = 0.018;
      const REST_LEN = 130;
      for (const e of this.edges) {
        const a = this.nodeById.get(e.source);
        const b = this.nodeById.get(e.target);
        if (!a || !b || !this._nodeVisible(a) || !this._nodeVisible(b)) continue;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.max(1, Math.sqrt(dx * dx + dy * dy));
        const diff = (dist - REST_LEN) * SPRING;
        const fx = (dx / dist) * diff;
        const fy = (dy / dist) * diff;
        a.fx = (a.fx || 0) + fx;
        a.fy = (a.fy || 0) + fy;
        b.fx = (b.fx || 0) - fx;
        b.fy = (b.fy || 0) - fy;
      }

      const DAMPING = 0.82;
      for (const n of nodes) {
        if (n === this.dragging) continue;
        n.vx = (n.vx + (n.fx || 0) * 0.016) * DAMPING;
        n.vy = (n.vy + (n.fy || 0) * 0.016) * DAMPING;
        n.x += n.vx;
        n.y += n.vy;
      }
    }

    _maybeStartIdlePulse(now) {
      if (now - this.lastInteraction < 3000) return;
      if (this.idlePulse && this.idlePulse.t < 1) return;
      if (!this.edges.length) return;
      if (Math.random() > 0.01) return;
      const e = this.edges[Math.floor(Math.random() * this.edges.length)];
      this.idlePulse = { edge: e, t: 0 };
    }

    _tick(now) {
      this._step();
      this._maybeStartIdlePulse(now);
      this._draw();
      requestAnimationFrame(this._tick.bind(this));
    }

    _draw() {
      const ctx = this.ctx;
      ctx.clearRect(0, 0, this.width, this.height);
      ctx.save();
      ctx.translate(this.width / 2, this.height / 2);
      ctx.scale(this.camera.zoom, this.camera.zoom);
      ctx.translate(-this.camera.x, -this.camera.y);

      const focused = this.hoveredNode || this.focusedNode;
      const focusedNeighbors = focused ? this.adjacency.get(focused.id) || new Set() : null;

      for (const e of this.edges) {
        const a = this.nodeById.get(e.source);
        const b = this.nodeById.get(e.target);
        if (!a || !b || !this._nodeVisible(a) || !this._nodeVisible(b)) continue;
        let alpha = 0.18;
        let lineWidth = 1;
        let strokeStyle = "rgba(255,255,255,0.5)";
        if (focused) {
          const connected = a.id === focused.id || b.id === focused.id;
          alpha = connected ? 0.85 : 0.04;
          if (connected) lineWidth = 1.6;
        }
        if (this.highlightPath.has(a.id) && this.highlightPath.has(b.id)) {
          strokeStyle = "rgba(232,114,44,0.95)";
          lineWidth = 2.4;
          alpha = 1;
        }
        ctx.globalAlpha = alpha;
        ctx.strokeStyle = strokeStyle;
        ctx.lineWidth = lineWidth;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }

      if (this.idlePulse) {
        const a = this.nodeById.get(this.idlePulse.edge.source);
        const b = this.nodeById.get(this.idlePulse.edge.target);
        if (a && b) {
          this.idlePulse.t += 0.012;
          const t = this.idlePulse.t;
          if (t <= 1) {
            const px = a.x + (b.x - a.x) * t;
            const py = a.y + (b.y - a.y) * t;
            ctx.globalAlpha = 1 - Math.abs(t - 0.5) * 0.6;
            ctx.fillStyle = "#e8722c";
            ctx.beginPath();
            ctx.arc(px, py, 2.6, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }

      for (const n of this.nodes) {
        if (!this._nodeVisible(n)) continue;
        let alpha = 1;
        if (focused) {
          const isFocused = n.id === focused.id;
          const isNeighbor = focusedNeighbors && focusedNeighbors.has(n.id);
          alpha = isFocused || isNeighbor ? 1 : 0.1;
        }
        ctx.globalAlpha = alpha;
        ctx.fillStyle = colorForType(n.type);
        const r = focused && n.id === focused.id ? n.radius * 1.25 : n.radius;
        ctx.beginPath();
        ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
        ctx.fill();

        if (this.highlightPath.has(n.id)) {
          ctx.globalAlpha = 1;
          ctx.strokeStyle = "#e8722c";
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(n.x, n.y, r + 3, 0, Math.PI * 2);
          ctx.stroke();
        }
      }
      ctx.globalAlpha = 1;

      ctx.font = "11px Inter, sans-serif";
      ctx.textAlign = "center";
      const placedLabels = [];
      const sortedForLabels = [...this.nodes]
        .filter((n) => this._nodeVisible(n))
        .sort((a, b) => (b.connections || 0) - (a.connections || 0));

      for (const n of sortedForLabels) {
        if (this.camera.zoom < 0.5 && (n.connections || 0) < 2) continue;
        if (focused) {
          const isFocused = n.id === focused.id;
          const isNeighbor = focusedNeighbors && focusedNeighbors.has(n.id);
          if (!isFocused && !isNeighbor) continue;
        }
        const label = n.title.length > 22 ? n.title.slice(0, 21) + "…" : n.title;
        const textWidth = ctx.measureText(label).width;
        const lx = n.x;
        const ly = n.y + n.radius + 13;
        const box = { x: lx - textWidth / 2 - 2, y: ly - 9, w: textWidth + 4, h: 12 };
        const overlaps = placedLabels.some(
          (p) => !(box.x + box.w < p.x || p.x + p.w < box.x || box.y + box.h < p.y || p.y + p.h < box.y)
        );
        if (overlaps) continue;
        placedLabels.push(box);
        ctx.fillStyle = "rgba(233,235,240,0.9)";
        ctx.fillText(label, lx, ly);
      }

      ctx.restore();
    }
  }

  window.JarvisGraph = ForceGraph;
})();
