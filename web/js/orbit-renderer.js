/**
 * Skjold-9 Orbit Renderer
 * High-performance Canvas 2D orbit visualization with:
 *   - Multi-layered sun glow
 *   - Earth orbit with glow halo
 *   - Gradient asteroid trails (green=far, red=near Earth)
 *   - Smooth pan & zoom with easing
 *   - High-DPI (devicePixelRatio) support
 *   - Multiple display modes (trajectory / anomaly / montecarlo)
 */

class OrbitRenderer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) throw new Error(`Canvas #${canvasId} not found`);
    this.ctx = this.canvas.getContext('2d');

    // Camera state (world coordinates in AU)
    this.camera = {
      x: 0,
      y: 0,
      zoom: 1.0,
      targetZoom: 1.0,
      targetX: 0,
      targetY: 0,
    };
    this.baseScale = 120; // base pixels per AU at zoom=1

    // Trajectory data
    this.earthOrbit = { x: [], y: [] };
    this.asteroidTrajectory = { x: [], y: [] };

    // Monte Carlo data
    this.monteCarloTrajectories = [];  // array of {x:[], y:[]}

    // Anomaly comparison data
    this.anomalyPredicted = { x: [], y: [] };
    this.anomalyActual = { x: [], y: [] };

    // Impact info
    this.impactDetected = false;
    this.impactPosition = { x: 0, y: 0 };

    // Animation
    this.animationProgress = 1.0;
    this.isAnimating = false;
    this.animationSpeed = 0.008;

    // Interaction
    this.isDragging = false;
    this.lastMouse = { x: 0, y: 0 };
    this.mouseWorld = { x: 0, y: 0 };

    // Display mode
    this.mode = 'trajectory'; // 'trajectory' | 'anomaly' | 'montecarlo'

    // Time tracking for sun pulse
    this.time = 0;

    // Cached dimensions
    this.width = 0;
    this.height = 0;
    this.dpr = window.devicePixelRatio || 1;

    this._setupEventListeners();
    this._resize();
    this._startRenderLoop();
  }

  // ═══════════════════ PUBLIC API ═══════════════════

  setTrajectory(earthData, asteroidData, impact = false) {
    this.earthOrbit = {
      x: earthData.earth_x || earthData.x || [],
      y: earthData.earth_y || earthData.y || [],
    };
    this.asteroidTrajectory = {
      x: asteroidData.asteroid_x || asteroidData.x || [],
      y: asteroidData.asteroid_y || asteroidData.y || [],
    };
    this.impactDetected = impact;
    this.mode = 'trajectory';
    this._startAnimation();
  }

  setAnomalyComparison(predicted, actual) {
    this.anomalyPredicted = {
      x: predicted.asteroid_x || predicted.x || [],
      y: predicted.asteroid_y || predicted.y || [],
    };
    this.anomalyActual = {
      x: actual.asteroid_x || actual.x || [],
      y: actual.asteroid_y || actual.y || [],
    };
    // Also keep earth orbit from predicted
    this.earthOrbit = {
      x: predicted.earth_x || [],
      y: predicted.earth_y || [],
    };
    this.mode = 'anomaly';
    this._startAnimation();
  }

  setMonteCarloTrajectories(trajectories) {
    this.monteCarloTrajectories = trajectories.map(t => ({
      x: t.asteroid_x || t.x || [],
      y: t.asteroid_y || t.y || [],
    }));
    // Keep existing earth orbit
    this.mode = 'montecarlo';
    this.animationProgress = 1.0;
    this.isAnimating = false;
  }

  clearAll() {
    this.earthOrbit = { x: [], y: [] };
    this.asteroidTrajectory = { x: [], y: [] };
    this.monteCarloTrajectories = [];
    this.anomalyPredicted = { x: [], y: [] };
    this.anomalyActual = { x: [], y: [] };
    this.impactDetected = false;
    this.animationProgress = 1.0;
    this.isAnimating = false;
  }

  setMode(mode) {
    this.mode = mode;
  }

  resetCamera() {
    this.camera.targetX = 0;
    this.camera.targetY = 0;
    this.camera.targetZoom = 1.0;
  }

  // ═══════════════════ EVENT LISTENERS ═══════════════════

  _setupEventListeners() {
    // Mouse wheel → zoom
    this.canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
      this.camera.targetZoom = Math.max(0.15, Math.min(50, this.camera.targetZoom * factor));

      // Update overlay
      const zoomEl = document.getElementById('overlay-zoom-value');
      if (zoomEl) zoomEl.textContent = `${this.camera.targetZoom.toFixed(1)}×`;
    }, { passive: false });

    // Mouse drag → pan
    this.canvas.addEventListener('mousedown', (e) => {
      this.isDragging = true;
      this.lastMouse.x = e.clientX;
      this.lastMouse.y = e.clientY;
      this.canvas.style.cursor = 'grabbing';
    });

    window.addEventListener('mousemove', (e) => {
      // Update mouse world coords for overlay
      const rect = this.canvas.getBoundingClientRect();
      const sx = e.clientX - rect.left;
      const sy = e.clientY - rect.top;
      this.mouseWorld = this._screenToWorld(sx, sy);

      const coordsEl = document.getElementById('overlay-coords-value');
      if (coordsEl && sx >= 0 && sy >= 0 && sx <= rect.width && sy <= rect.height) {
        coordsEl.textContent = `${this.mouseWorld.x.toFixed(2)}, ${this.mouseWorld.y.toFixed(2)} AU`;
      }

      if (!this.isDragging) return;
      const dx = e.clientX - this.lastMouse.x;
      const dy = e.clientY - this.lastMouse.y;
      const scale = this.baseScale * this.camera.zoom;
      this.camera.targetX -= dx / scale;
      this.camera.targetY += dy / scale; // invert Y
      this.lastMouse.x = e.clientX;
      this.lastMouse.y = e.clientY;
    });

    window.addEventListener('mouseup', () => {
      this.isDragging = false;
      this.canvas.style.cursor = 'crosshair';
    });

    // Touch support
    this.canvas.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        this.isDragging = true;
        this.lastMouse.x = e.touches[0].clientX;
        this.lastMouse.y = e.touches[0].clientY;
      }
    }, { passive: true });

    this.canvas.addEventListener('touchmove', (e) => {
      if (!this.isDragging || e.touches.length !== 1) return;
      const dx = e.touches[0].clientX - this.lastMouse.x;
      const dy = e.touches[0].clientY - this.lastMouse.y;
      const scale = this.baseScale * this.camera.zoom;
      this.camera.targetX -= dx / scale;
      this.camera.targetY += dy / scale;
      this.lastMouse.x = e.touches[0].clientX;
      this.lastMouse.y = e.touches[0].clientY;
    }, { passive: true });

    this.canvas.addEventListener('touchend', () => {
      this.isDragging = false;
    }, { passive: true });

    // Double click → reset
    this.canvas.addEventListener('dblclick', () => {
      this.resetCamera();
    });

    // Window resize
    window.addEventListener('resize', () => this._resize());
  }

  // ═══════════════════ CANVAS SIZING ═══════════════════

  _resize() {
    const container = this.canvas.parentElement;
    const rect = container.getBoundingClientRect();
    this.width = rect.width;
    this.height = rect.height;
    this.dpr = window.devicePixelRatio || 1;

    this.canvas.width = this.width * this.dpr;
    this.canvas.height = this.height * this.dpr;
    this.canvas.style.width = `${this.width}px`;
    this.canvas.style.height = `${this.height}px`;
  }

  // ═══════════════════ COORDINATE TRANSFORMS ═══════════════════

  _worldToScreen(wx, wy) {
    const scale = this.baseScale * this.camera.zoom * this.dpr;
    const cx = (this.canvas.width) / 2;
    const cy = (this.canvas.height) / 2;
    return {
      x: cx + (wx - this.camera.x) * scale,
      y: cy - (wy - this.camera.y) * scale, // invert Y
    };
  }

  _screenToWorld(sx, sy) {
    const scale = this.baseScale * this.camera.zoom;
    const cx = this.width / 2;
    const cy = this.height / 2;
    return {
      x: this.camera.x + (sx - cx) / scale,
      y: this.camera.y - (sy - cy) / scale,
    };
  }

  // ═══════════════════ ANIMATION LOOP ═══════════════════

  _startAnimation() {
    this.animationProgress = 0;
    this.isAnimating = true;
  }

  _startRenderLoop() {
    const loop = () => {
      this._update();
      this._render();
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  _update() {
    this.time += 0.016; // ~60fps

    // Smooth camera lerp
    const lerp = 0.12;
    this.camera.x += (this.camera.targetX - this.camera.x) * lerp;
    this.camera.y += (this.camera.targetY - this.camera.y) * lerp;
    this.camera.zoom += (this.camera.targetZoom - this.camera.zoom) * lerp;

    // Animation progress
    if (this.isAnimating) {
      this.animationProgress += this.animationSpeed;
      if (this.animationProgress >= 1.0) {
        this.animationProgress = 1.0;
        this.isAnimating = false;
      }
    }
  }

  // ═══════════════════ MAIN RENDER ═══════════════════

  _render() {
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;

    // Clear
    ctx.fillStyle = '#07071a';
    ctx.fillRect(0, 0, w, h);

    // Subtle radial background gradient
    const bgGrad = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, Math.max(w, h) * 0.6);
    bgGrad.addColorStop(0, 'rgba(30, 25, 60, 0.3)');
    bgGrad.addColorStop(1, 'rgba(7, 7, 26, 0)');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, w, h);

    // Draw elements
    this._drawGrid();
    this._drawEarthOrbitCircle();
    this._drawSun();

    // Mode-specific rendering
    switch (this.mode) {
      case 'trajectory':
        this._drawTrajectoryMode();
        break;
      case 'anomaly':
        this._drawAnomalyMode();
        break;
      case 'montecarlo':
        this._drawMonteCarloMode();
        break;
    }

    // Draw Earth
    if (this.earthOrbit.x.length > 0) {
      const idx = Math.min(
        Math.floor(this.animationProgress * (this.earthOrbit.x.length - 1)),
        this.earthOrbit.x.length - 1
      );
      this._drawEarth(this.earthOrbit.x[idx], this.earthOrbit.y[idx]);
    }

    // Impact zone effect
    if (this.impactDetected) {
      this._drawImpactZone();
    }

    // Scale bar
    this._drawScaleBar();
  }

  // ═══════════════════ GRID ═══════════════════

  _drawGrid() {
    const ctx = this.ctx;
    const scale = this.baseScale * this.camera.zoom * this.dpr;

    // Determine grid spacing based on zoom
    let gridStep = 1.0; // AU
    if (this.camera.zoom > 3) gridStep = 0.5;
    if (this.camera.zoom > 8) gridStep = 0.25;
    if (this.camera.zoom < 0.5) gridStep = 2.0;

    const viewLeft = this._screenToWorld(0, 0).x / (1 / this.dpr);
    const viewRight = this._screenToWorld(this.width, 0).x / (1 / this.dpr);
    const viewTop = this._screenToWorld(0, 0).y / (1 / this.dpr);
    const viewBottom = this._screenToWorld(0, this.height).y / (1 / this.dpr);

    // Recalculate view bounds properly
    const tl = this._screenToWorld(0, 0);
    const br = this._screenToWorld(this.width, this.height);
    const minX = Math.floor(tl.x / gridStep) * gridStep;
    const maxX = Math.ceil(br.x / gridStep) * gridStep;
    const minY = Math.floor(br.y / gridStep) * gridStep;
    const maxY = Math.ceil(tl.y / gridStep) * gridStep;

    ctx.lineWidth = 1;

    // Vertical grid lines
    for (let x = minX; x <= maxX; x += gridStep) {
      const s = this._worldToScreen(x, 0);
      const isAxis = Math.abs(x) < 0.001;
      ctx.strokeStyle = isAxis ? 'rgba(100, 100, 160, 0.25)' : 'rgba(60, 60, 100, 0.1)';
      ctx.beginPath();
      ctx.moveTo(s.x, 0);
      ctx.lineTo(s.x, this.canvas.height);
      ctx.stroke();

      // Labels
      if (Math.abs(x) > 0.001) {
        const labelPos = this._worldToScreen(x, 0);
        ctx.fillStyle = 'rgba(100, 100, 160, 0.35)';
        ctx.font = `${10 * this.dpr}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.fillText(`${x.toFixed(gridStep < 1 ? 1 : 0)}`, labelPos.x, labelPos.y + 14 * this.dpr);
      }
    }

    // Horizontal grid lines
    for (let y = minY; y <= maxY; y += gridStep) {
      const s = this._worldToScreen(0, y);
      const isAxis = Math.abs(y) < 0.001;
      ctx.strokeStyle = isAxis ? 'rgba(100, 100, 160, 0.25)' : 'rgba(60, 60, 100, 0.1)';
      ctx.beginPath();
      ctx.moveTo(0, s.y);
      ctx.lineTo(this.canvas.width, s.y);
      ctx.stroke();

      if (Math.abs(y) > 0.001) {
        const labelPos = this._worldToScreen(0, y);
        ctx.fillStyle = 'rgba(100, 100, 160, 0.35)';
        ctx.font = `${10 * this.dpr}px Inter, sans-serif`;
        ctx.textAlign = 'left';
        ctx.fillText(`${y.toFixed(gridStep < 1 ? 1 : 0)}`, labelPos.x + 6 * this.dpr, labelPos.y - 4 * this.dpr);
      }
    }
  }

  // ═══════════════════ SUN ═══════════════════

  _drawSun() {
    const ctx = this.ctx;
    const s = this._worldToScreen(0, 0);
    const pulse = 1.0 + 0.08 * Math.sin(this.time * 2.5);
    const scale = this.baseScale * this.camera.zoom * this.dpr;

    // Outer glow — large
    const outerR = Math.max(60, scale * 0.5) * pulse;
    const outerGrad = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, outerR);
    outerGrad.addColorStop(0, 'rgba(255, 167, 38, 0.15)');
    outerGrad.addColorStop(0.4, 'rgba(255, 140, 0, 0.06)');
    outerGrad.addColorStop(1, 'rgba(255, 100, 0, 0)');
    ctx.fillStyle = outerGrad;
    ctx.beginPath();
    ctx.arc(s.x, s.y, outerR, 0, Math.PI * 2);
    ctx.fill();

    // Mid glow
    const midR = Math.max(25, scale * 0.2) * pulse;
    const midGrad = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, midR);
    midGrad.addColorStop(0, 'rgba(255, 220, 100, 0.6)');
    midGrad.addColorStop(0.5, 'rgba(255, 167, 38, 0.25)');
    midGrad.addColorStop(1, 'rgba(255, 140, 0, 0)');
    ctx.fillStyle = midGrad;
    ctx.beginPath();
    ctx.arc(s.x, s.y, midR, 0, Math.PI * 2);
    ctx.fill();

    // Inner core
    const coreR = Math.max(6, scale * 0.05) * pulse;
    const coreGrad = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, coreR);
    coreGrad.addColorStop(0, 'rgba(255, 255, 240, 1)');
    coreGrad.addColorStop(0.4, 'rgba(255, 230, 150, 0.9)');
    coreGrad.addColorStop(1, 'rgba(255, 200, 80, 0)');
    ctx.fillStyle = coreGrad;
    ctx.beginPath();
    ctx.arc(s.x, s.y, coreR, 0, Math.PI * 2);
    ctx.fill();

    // Label
    ctx.fillStyle = 'rgba(255, 200, 100, 0.5)';
    ctx.font = `${10 * this.dpr}px Orbitron, sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillText('☉', s.x, s.y + (coreR + 16 * this.dpr));
  }

  // ═══════════════════ EARTH ORBIT CIRCLE ═══════════════════

  _drawEarthOrbitCircle() {
    const ctx = this.ctx;
    const center = this._worldToScreen(0, 0);
    const edgePoint = this._worldToScreen(1, 0);
    const radiusPx = edgePoint.x - center.x;

    ctx.strokeStyle = 'rgba(66, 165, 245, 0.12)';
    ctx.lineWidth = 1.5 * this.dpr;
    ctx.setLineDash([6 * this.dpr, 8 * this.dpr]);
    ctx.beginPath();
    ctx.arc(center.x, center.y, radiusPx, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);

    // "1 AU" label
    const labelPos = this._worldToScreen(0.72, 0.72);
    ctx.fillStyle = 'rgba(66, 165, 245, 0.3)';
    ctx.font = `${9 * this.dpr}px Inter, sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillText('1 AU', labelPos.x, labelPos.y);
  }

  // ═══════════════════ EARTH ═══════════════════

  _drawEarth(wx, wy) {
    const ctx = this.ctx;
    const s = this._worldToScreen(wx, wy);
    const r = Math.max(4, 6 * this.dpr);

    // Glow
    const glowR = r * 5;
    const glowGrad = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, glowR);
    glowGrad.addColorStop(0, 'rgba(66, 165, 245, 0.25)');
    glowGrad.addColorStop(0.5, 'rgba(66, 165, 245, 0.08)');
    glowGrad.addColorStop(1, 'rgba(66, 165, 245, 0)');
    ctx.fillStyle = glowGrad;
    ctx.beginPath();
    ctx.arc(s.x, s.y, glowR, 0, Math.PI * 2);
    ctx.fill();

    // Body
    const bodyGrad = ctx.createRadialGradient(s.x - r * 0.3, s.y - r * 0.3, 0, s.x, s.y, r);
    bodyGrad.addColorStop(0, '#90caf9');
    bodyGrad.addColorStop(0.7, '#42a5f5');
    bodyGrad.addColorStop(1, '#1565c0');
    ctx.fillStyle = bodyGrad;
    ctx.beginPath();
    ctx.arc(s.x, s.y, r, 0, Math.PI * 2);
    ctx.fill();

    // Label
    ctx.fillStyle = 'rgba(66, 165, 245, 0.6)';
    ctx.font = `${10 * this.dpr}px Orbitron, sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillText('⊕', s.x, s.y + r + 14 * this.dpr);
  }

  // ═══════════════════ TRAJECTORY DRAWING ═══════════════════

  _drawPath(xArr, yArr, color, options = {}) {
    if (!xArr || xArr.length < 2) return;

    const ctx = this.ctx;
    const {
      dashed = false,
      alpha = 1.0,
      lineWidth = 2,
      gradient = false,
      trail = false,
      glowColor = null,
    } = options;

    const len = xArr.length;
    const drawLen = trail
      ? Math.floor(this.animationProgress * len)
      : len;

    if (drawLen < 2) return;

    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.lineWidth = lineWidth * this.dpr;

    if (dashed) {
      ctx.setLineDash([8 * this.dpr, 6 * this.dpr]);
    }

    // Optional glow layer
    if (glowColor) {
      ctx.save();
      ctx.strokeStyle = glowColor;
      ctx.lineWidth = (lineWidth + 4) * this.dpr;
      ctx.globalAlpha = alpha * 0.3;
      ctx.filter = `blur(${4 * this.dpr}px)`;
      ctx.beginPath();
      const start = this._worldToScreen(xArr[0], yArr[0]);
      ctx.moveTo(start.x, start.y);
      for (let i = 1; i < drawLen; i++) {
        const p = this._worldToScreen(xArr[i], yArr[i]);
        ctx.lineTo(p.x, p.y);
      }
      ctx.stroke();
      ctx.restore();
    }

    // Main line
    if (gradient && this.earthOrbit.x.length > 0) {
      // Draw segments with color based on proximity to Earth
      for (let i = 1; i < drawLen; i++) {
        const p0 = this._worldToScreen(xArr[i - 1], yArr[i - 1]);
        const p1 = this._worldToScreen(xArr[i], yArr[i]);

        // Calculate distance to earth at same time index
        const eIdx = Math.min(i, this.earthOrbit.x.length - 1);
        const dx = xArr[i] - (this.earthOrbit.x[eIdx] || 0);
        const dy = yArr[i] - (this.earthOrbit.y[eIdx] || 0);
        const dist = Math.sqrt(dx * dx + dy * dy);

        // Map distance to color: close=red, far=teal
        const t = Math.min(1, dist / 2.0);
        const r = Math.round(255 * (1 - t) + 78 * t);
        const g = Math.round(107 * (1 - t) + 205 * t);
        const b = Math.round(107 * (1 - t) + 196 * t);

        // Fade trail: more opaque at the head
        const trailAlpha = trail
          ? 0.2 + 0.8 * (i / drawLen)
          : 1.0;

        ctx.globalAlpha = alpha * trailAlpha;
        ctx.strokeStyle = `rgb(${r}, ${g}, ${b})`;
        ctx.beginPath();
        ctx.moveTo(p0.x, p0.y);
        ctx.lineTo(p1.x, p1.y);
        ctx.stroke();
      }
    } else {
      ctx.strokeStyle = color;
      ctx.beginPath();
      const start = this._worldToScreen(xArr[0], yArr[0]);
      ctx.moveTo(start.x, start.y);
      for (let i = 1; i < drawLen; i++) {
        const p = this._worldToScreen(xArr[i], yArr[i]);
        ctx.lineTo(p.x, p.y);

        // Fade trail
        if (trail) {
          ctx.globalAlpha = alpha * (0.2 + 0.8 * (i / drawLen));
        }
      }
      ctx.stroke();
    }

    ctx.setLineDash([]);
    ctx.restore();
  }

  _drawAsteroidHead(xArr, yArr, color = '#ff6b6b') {
    if (!xArr || xArr.length < 2) return;
    const ctx = this.ctx;
    const idx = Math.min(
      Math.floor(this.animationProgress * (xArr.length - 1)),
      xArr.length - 1
    );
    const s = this._worldToScreen(xArr[idx], yArr[idx]);
    const r = Math.max(3, 4 * this.dpr);

    // Glow
    const glowGrad = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, r * 5);
    glowGrad.addColorStop(0, color.replace(')', ', 0.3)').replace('rgb', 'rgba'));
    glowGrad.addColorStop(1, 'rgba(0,0,0,0)');

    // Use simpler glow
    ctx.save();
    ctx.shadowColor = color;
    ctx.shadowBlur = 15 * this.dpr;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(s.x, s.y, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // Bright core
    ctx.fillStyle = '#fff';
    ctx.beginPath();
    ctx.arc(s.x, s.y, r * 0.4, 0, Math.PI * 2);
    ctx.fill();
  }

  // ═══════════════════ MODE RENDERERS ═══════════════════

  _drawTrajectoryMode() {
    // Earth orbit trace
    if (this.earthOrbit.x.length > 0) {
      this._drawPath(
        this.earthOrbit.x, this.earthOrbit.y,
        'rgba(66, 165, 245, 0.3)',
        { lineWidth: 1.5, trail: true }
      );
    }

    // Asteroid trajectory with gradient
    if (this.asteroidTrajectory.x.length > 0) {
      this._drawPath(
        this.asteroidTrajectory.x, this.asteroidTrajectory.y,
        '#ff6b6b',
        { lineWidth: 2, gradient: true, trail: true, glowColor: 'rgba(255, 107, 107, 0.4)' }
      );
      this._drawAsteroidHead(
        this.asteroidTrajectory.x, this.asteroidTrajectory.y,
        '#ff6b6b'
      );
    }

    // Starting position marker
    if (this.asteroidTrajectory.x.length > 0) {
      const startS = this._worldToScreen(
        this.asteroidTrajectory.x[0],
        this.asteroidTrajectory.y[0]
      );
      const ctx = this.ctx;
      ctx.strokeStyle = 'rgba(255, 107, 107, 0.4)';
      ctx.lineWidth = 1 * this.dpr;
      ctx.setLineDash([3 * this.dpr, 3 * this.dpr]);
      ctx.beginPath();
      ctx.arc(startS.x, startS.y, 10 * this.dpr, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = 'rgba(255, 107, 107, 0.5)';
      ctx.font = `${9 * this.dpr}px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.fillText('START', startS.x, startS.y - 14 * this.dpr);
    }
  }

  _drawAnomalyMode() {
    // Earth orbit trace
    if (this.earthOrbit.x.length > 0) {
      this._drawPath(
        this.earthOrbit.x, this.earthOrbit.y,
        'rgba(66, 165, 245, 0.25)',
        { lineWidth: 1.5, trail: true }
      );
    }

    // Predicted (green dashed)
    if (this.anomalyPredicted.x.length > 0) {
      this._drawPath(
        this.anomalyPredicted.x, this.anomalyPredicted.y,
        '#4ecdc4',
        { lineWidth: 2, dashed: true, trail: true, alpha: 0.7 }
      );
    }

    // Actual (red solid)
    if (this.anomalyActual.x.length > 0) {
      this._drawPath(
        this.anomalyActual.x, this.anomalyActual.y,
        '#ff6b6b',
        { lineWidth: 2, trail: true, glowColor: 'rgba(255, 107, 107, 0.3)' }
      );
      this._drawAsteroidHead(
        this.anomalyActual.x, this.anomalyActual.y,
        '#ff6b6b'
      );
    }

    // Legend
    this._drawAnomalyLegend();
  }

  _drawMonteCarloMode() {
    // Earth orbit
    if (this.earthOrbit.x.length > 0) {
      this._drawPath(
        this.earthOrbit.x, this.earthOrbit.y,
        'rgba(66, 165, 245, 0.3)',
        { lineWidth: 1.5 }
      );
    }

    // Monte Carlo trajectories (semi-transparent)
    const colors = ['#6c63ff', '#ff6b6b', '#4ecdc4', '#ffd93d', '#ff9ff3'];
    for (let i = 0; i < this.monteCarloTrajectories.length; i++) {
      const traj = this.monteCarloTrajectories[i];
      if (!traj.x || traj.x.length < 2) continue;
      this._drawPath(
        traj.x, traj.y,
        colors[i % colors.length],
        { lineWidth: 1, alpha: 0.25 }
      );
    }
  }

  _drawAnomalyLegend() {
    const ctx = this.ctx;
    const x = 20 * this.dpr;
    const y = this.canvas.height - 60 * this.dpr;

    ctx.save();
    // Background
    ctx.fillStyle = 'rgba(10, 10, 30, 0.7)';
    const lw = 160 * this.dpr;
    const lh = 50 * this.dpr;
    ctx.beginPath();
    ctx.roundRect(x, y, lw, lh, 6 * this.dpr);
    ctx.fill();

    // Predicted
    ctx.strokeStyle = '#4ecdc4';
    ctx.lineWidth = 2 * this.dpr;
    ctx.setLineDash([6 * this.dpr, 4 * this.dpr]);
    ctx.beginPath();
    ctx.moveTo(x + 10 * this.dpr, y + 18 * this.dpr);
    ctx.lineTo(x + 36 * this.dpr, y + 18 * this.dpr);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = '#4ecdc4';
    ctx.font = `${10 * this.dpr}px Inter, sans-serif`;
    ctx.textAlign = 'left';
    ctx.fillText('Prediksi', x + 42 * this.dpr, y + 22 * this.dpr);

    // Actual
    ctx.strokeStyle = '#ff6b6b';
    ctx.lineWidth = 2 * this.dpr;
    ctx.beginPath();
    ctx.moveTo(x + 10 * this.dpr, y + 36 * this.dpr);
    ctx.lineTo(x + 36 * this.dpr, y + 36 * this.dpr);
    ctx.stroke();

    ctx.fillStyle = '#ff6b6b';
    ctx.fillText('Aktual (anomali)', x + 42 * this.dpr, y + 40 * this.dpr);

    ctx.restore();
  }

  // ═══════════════════ IMPACT ZONE ═══════════════════

  _drawImpactZone() {
    if (this.earthOrbit.x.length === 0) return;

    const ctx = this.ctx;
    const lastIdx = this.earthOrbit.x.length - 1;
    const s = this._worldToScreen(this.earthOrbit.x[lastIdx], this.earthOrbit.y[lastIdx]);

    const pulse = 1.0 + 0.4 * Math.sin(this.time * 4);
    const r = 30 * this.dpr * pulse;

    ctx.save();
    ctx.strokeStyle = `rgba(255, 107, 107, ${0.3 + 0.2 * Math.sin(this.time * 4)})`;
    ctx.lineWidth = 2 * this.dpr;
    ctx.beginPath();
    ctx.arc(s.x, s.y, r, 0, Math.PI * 2);
    ctx.stroke();

    ctx.strokeStyle = `rgba(255, 107, 107, ${0.15 + 0.1 * Math.sin(this.time * 3)})`;
    ctx.beginPath();
    ctx.arc(s.x, s.y, r * 1.5, 0, Math.PI * 2);
    ctx.stroke();

    // "IMPACT" label
    ctx.fillStyle = `rgba(255, 107, 107, ${0.6 + 0.3 * Math.sin(this.time * 4)})`;
    ctx.font = `bold ${11 * this.dpr}px Orbitron, sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillText('⚠ IMPACT', s.x, s.y - r - 8 * this.dpr);

    ctx.restore();
  }

  // ═══════════════════ SCALE BAR ═══════════════════

  _drawScaleBar() {
    const ctx = this.ctx;
    const scale = this.baseScale * this.camera.zoom * this.dpr;
    const barAU = this.camera.zoom > 2 ? 0.5 : 1.0;
    const barPx = barAU * scale;

    const x = this.canvas.width - barPx - 30 * this.dpr;
    const y = this.canvas.height - 25 * this.dpr;

    ctx.strokeStyle = 'rgba(140, 140, 180, 0.4)';
    ctx.lineWidth = 1.5 * this.dpr;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + barPx, y);
    // End caps
    ctx.moveTo(x, y - 4 * this.dpr);
    ctx.lineTo(x, y + 4 * this.dpr);
    ctx.moveTo(x + barPx, y - 4 * this.dpr);
    ctx.lineTo(x + barPx, y + 4 * this.dpr);
    ctx.stroke();

    ctx.fillStyle = 'rgba(140, 140, 180, 0.5)';
    ctx.font = `${9 * this.dpr}px Inter, sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillText(`${barAU} AU`, x + barPx / 2, y - 8 * this.dpr);
  }
}
