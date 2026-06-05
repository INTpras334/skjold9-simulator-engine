/**
 * Skjold-9 Main Application Controller
 * Orchestrates UI, API calls, and visualization.
 */

class SkjoldApp {
  constructor() {
    this.api = api;           // from api-client.js
    this.renderer = null;     // OrbitRenderer (initialized in init())
    this.state = {
      r_x: -1.2,
      r_y: 0.5,
      v_x: 18.0,
      v_y: -4.5,
      anomaly: false,
      anomaly_strength: 1.0,
      n_sims: 100,
      sigma_pos_au: 0.001,
      sigma_vel_ms: 10.0,
      isSimulating: false,
      currentMode: 'trajectory',
    };
    this.debounceTimer = null;
    this.monteCarloController = null;
    this._lastTrajectoryResult = null;
  }

  // ═══════════════════ INITIALIZATION ═══════════════════

  async init() {
    this.renderer = new OrbitRenderer('orbit-canvas');
    this._bindSliders();
    this._bindButtons();
    this._bindKeyboard();

    // Load defaults from API
    try {
      const defaults = await this.api.getDefaults();
      this._applyDefaults(defaults);
    } catch (e) {
      console.warn('Using hardcoded defaults:', e.message);
    }

    // Run initial simulation
    await this.runTrajectory();
  }

  _applyDefaults(defaults) {
    const mapping = {
      r_x:              { slider: 'slider-rx',               display: 'value-rx',          source: 'trajectory' },
      r_y:              { slider: 'slider-ry',               display: 'value-ry',          source: 'trajectory' },
      v_x:              { slider: 'slider-vx',               display: 'value-vx',          source: 'trajectory' },
      v_y:              { slider: 'slider-vy',               display: 'value-vy',          source: 'trajectory' },
      anomaly_strength: { slider: 'slider-anomaly-strength', display: 'value-anomaly-strength', source: 'trajectory' },
      n_sims:           { slider: 'slider-nsims',            display: 'value-nsims',       source: 'monte_carlo' },
      sigma_pos_au:     { slider: 'slider-sigma-pos',        display: 'value-sigma-pos',   source: 'monte_carlo' },
      sigma_vel_ms:     { slider: 'slider-sigma-vel',        display: 'value-sigma-vel',   source: 'monte_carlo' },
    };

    for (const [key, ids] of Object.entries(mapping)) {
      const sourceObj = defaults[ids.source];
      if (sourceObj && sourceObj[key] !== undefined) {
        this.state[key] = sourceObj[key];
        const slider = document.getElementById(ids.slider);
        const display = document.getElementById(ids.display);
        if (slider) slider.value = sourceObj[key];
        if (display) display.textContent = this._formatSliderValue(key, sourceObj[key]);
      }
    }

    // Anomaly toggle
    const trajDefaults = defaults.trajectory;
    if (trajDefaults && trajDefaults.anomaly !== undefined) {
      this.state.anomaly = trajDefaults.anomaly;
      const toggle = document.getElementById('toggle-anomaly');
      if (toggle) toggle.checked = trajDefaults.anomaly;
    }
  }

  _formatSliderValue(key, val) {
    const v = parseFloat(val);
    switch (key) {
      case 'r_x':
      case 'r_y':
        return v.toFixed(2);
      case 'v_x':
      case 'v_y':
        return v.toFixed(1);
      case 'anomaly_strength':
        return v.toFixed(1);
      case 'n_sims':
        return Math.round(v).toString();
      case 'sigma_pos_au':
        return v.toFixed(3);
      case 'sigma_vel_ms':
        return Math.round(v).toString();
      default:
        return v.toString();
    }
  }

  // ═══════════════════ SLIDER BINDINGS ═══════════════════

  _bindSliders() {
    const sliders = [
      { id: 'slider-rx',               key: 'r_x',              displayId: 'value-rx' },
      { id: 'slider-ry',               key: 'r_y',              displayId: 'value-ry' },
      { id: 'slider-vx',               key: 'v_x',              displayId: 'value-vx' },
      { id: 'slider-vy',               key: 'v_y',              displayId: 'value-vy' },
      { id: 'slider-anomaly-strength', key: 'anomaly_strength', displayId: 'value-anomaly-strength' },
      { id: 'slider-nsims',            key: 'n_sims',           displayId: 'value-nsims' },
      { id: 'slider-sigma-pos',        key: 'sigma_pos_au',     displayId: 'value-sigma-pos' },
      { id: 'slider-sigma-vel',        key: 'sigma_vel_ms',     displayId: 'value-sigma-vel' },
    ];

    // Trajectory-affecting sliders (trigger re-simulation)
    const trajectoryKeys = new Set(['r_x', 'r_y', 'v_x', 'v_y', 'anomaly_strength']);

    for (const { id, key, displayId } of sliders) {
      const slider = document.getElementById(id);
      const display = document.getElementById(displayId);
      if (!slider) continue;

      slider.addEventListener('input', () => {
        const val = parseFloat(slider.value);
        this.state[key] = val;
        if (display) {
          display.textContent = this._formatSliderValue(key, val);
        }

        // Debounce trajectory recalculation
        if (trajectoryKeys.has(key)) {
          this._debouncedRunTrajectory();
        }
      });
    }

    // Anomaly toggle
    const toggle = document.getElementById('toggle-anomaly');
    if (toggle) {
      toggle.addEventListener('change', () => {
        this.state.anomaly = toggle.checked;
        this._debouncedRunTrajectory();
      });
    }
  }

  _debouncedRunTrajectory() {
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
      this.runTrajectory();
    }, 300);
  }

  // ═══════════════════ BUTTON BINDINGS ═══════════════════

  _bindButtons() {
    const mcBtn = document.getElementById('btn-monte-carlo');
    if (mcBtn) {
      mcBtn.addEventListener('click', () => this.runMonteCarlo());
    }

    const anomBtn = document.getElementById('btn-anomaly-compare');
    if (anomBtn) {
      anomBtn.addEventListener('click', () => this.runAnomaly());
    }

    const resetBtn = document.getElementById('btn-reset-camera');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        if (this.renderer) this.renderer.resetCamera();
      });
    }
  }

  _bindKeyboard() {
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.monteCarloController) {
        this.monteCarloController.abort();
        this.monteCarloController = null;
        this._hideProgress();
        this._setButtonState('btn-monte-carlo', false);
      }
      if (e.key === 'r' && !e.ctrlKey && !e.metaKey && e.target.tagName !== 'INPUT') {
        if (this.renderer) this.renderer.resetCamera();
      }
    });
  }

  // ═══════════════════ TRAJECTORY SIMULATION ═══════════════════

  async runTrajectory() {
    if (this.state.isSimulating) return;

    this._showLoading();
    this._setMode('trajectory');

    try {
      const result = await this.api.simulateTrajectory({
        r_x: this.state.r_x,
        r_y: this.state.r_y,
        v_x: this.state.v_x,
        v_y: this.state.v_y,
        anomaly: this.state.anomaly,
        anomaly_strength: this.state.anomaly_strength,
      });

      this._lastTrajectoryResult = result;

      // Update renderer
      this.renderer.setTrajectory(
        { earth_x: result.earth_x, earth_y: result.earth_y },
        { asteroid_x: result.asteroid_x, asteroid_y: result.asteroid_y },
        result.impact
      );

      // Update stats
      this._updateStatsCards(result);
      this._updateImpactGauge(result.impact ? 100 : 0);

    } catch (err) {
      console.error('Trajectory simulation error:', err);
      this._showError('Gagal menghitung trajektori: ' + err.message);
    } finally {
      this._hideLoading();
    }
  }

  // ═══════════════════ ANOMALY SIMULATION ═══════════════════

  async runAnomaly() {
    if (this.state.isSimulating) return;
    this.state.isSimulating = true;

    this._showLoading();
    this._setMode('anomaly');
    this._setButtonState('btn-anomaly-compare', true);

    try {
      const result = await this.api.simulateAnomaly({
        r_x: this.state.r_x,
        r_y: this.state.r_y,
        v_x: this.state.v_x,
        v_y: this.state.v_y,
        anomaly_strength: this.state.anomaly_strength,
      });

      // Update renderer
      this.renderer.setAnomalyComparison(result.predicted, result.actual);

      // Update deviation chart
      if (result.deviation_km && result.time_days) {
        this._updateDeviationChart(result.deviation_km, result.time_days, result.threshold_day);
        const devCard = document.getElementById('deviation-card');
        if (devCard) devCard.style.display = '';
      }

      // Update stats with actual trajectory info
      this._updateStatsCards(result.actual);

      // Summary
      const summary = document.getElementById('deviation-summary');
      if (summary) {
        const maxDev = result.max_deviation_km || 0;
        summary.innerHTML = `
          <span class="deviation-stat">Deviasi Maksimum: <strong>${this._formatDistance(maxDev)}</strong></span>
          ${result.threshold_day ? `<span class="deviation-stat">Melewati ambang pada hari: <strong>${Math.round(result.threshold_day)}</strong></span>` : ''}
        `;
      }

    } catch (err) {
      console.error('Anomaly simulation error:', err);
      this._showError('Gagal menghitung anomali: ' + err.message);
    } finally {
      this.state.isSimulating = false;
      this._hideLoading();
      this._setButtonState('btn-anomaly-compare', false);
    }
  }

  // ═══════════════════ MONTE CARLO SIMULATION ═══════════════════

  async runMonteCarlo() {
    if (this.state.isSimulating) return;
    this.state.isSimulating = true;

    // Cancel previous MC if running
    if (this.monteCarloController) {
      this.monteCarloController.abort();
    }

    this._setButtonState('btn-monte-carlo', true);
    this._showProgress(0, this.state.n_sims, 0);
    this._setMode('montecarlo');

    this.monteCarloController = this.api.streamMonteCarlo(
      {
        r_x: this.state.r_x,
        r_y: this.state.r_y,
        v_x: this.state.v_x,
        v_y: this.state.v_y,
        n_sims: this.state.n_sims,
        sigma_pos_au: this.state.sigma_pos_au,
        sigma_vel_ms: this.state.sigma_vel_ms,
        anomaly: this.state.anomaly,
        anomaly_strength: this.state.anomaly_strength,
      },
      {
        onProgress: (data) => {
          this._showProgress(data.completed, data.total, data.impacts_so_far);
        },
        onResult: (data) => {
          this.state.isSimulating = false;
          this.monteCarloController = null;
          this._hideProgress();
          this._setButtonState('btn-monte-carlo', false);

          // Update gauge
          const prob = (data.impact_probability !== undefined)
            ? data.impact_probability * 100
            : (data.impacts / data.total_sims) * 100;
          this._updateImpactGauge(prob);

          // Update histogram
          if (data.min_distances_km) {
            this._updateHistogram(data.min_distances_km);
            const histCard = document.getElementById('histogram-card');
            if (histCard) histCard.style.display = '';
          }

          // Show sample trajectories on canvas
          if (data.sample_trajectories && data.sample_trajectories.length > 0) {
            this.renderer.setMonteCarloTrajectories(data.sample_trajectories);
          }

          // Update summary
          const summary = document.getElementById('histogram-summary');
          if (summary) {
            summary.innerHTML = `
              <span>Total: <strong>${data.total_sims}</strong> simulasi</span>
              <span>Impact: <strong>${data.impacts}</strong> (${prob.toFixed(1)}%)</span>
            `;
          }
        },
        onError: (err) => {
          this.state.isSimulating = false;
          this.monteCarloController = null;
          this._hideProgress();
          this._setButtonState('btn-monte-carlo', false);
          console.error('Monte Carlo error:', err);
          this._showError('Monte Carlo error: ' + err.message);
        },
      }
    );
  }

  // ═══════════════════ IMPACT GAUGE ═══════════════════

  _updateImpactGauge(probability) {
    const prob = Math.max(0, Math.min(100, probability));

    // Arc fill: total arc length is ~251.33 (π * 80)
    const arcLength = 251.33;
    const fillLength = arcLength * (1 - prob / 100);
    const gaugeFill = document.getElementById('gauge-fill');
    if (gaugeFill) {
      gaugeFill.style.transition = 'stroke-dashoffset 1s cubic-bezier(0.4, 0, 0.2, 1)';
      gaugeFill.setAttribute('stroke-dashoffset', fillLength.toString());
    }

    // Needle rotation: -90° (0%) to +90° (100%)
    const angle = -90 + (prob / 100) * 180;
    const needle = document.getElementById('gauge-needle');
    if (needle) {
      needle.style.transition = 'transform 1s cubic-bezier(0.4, 0, 0.2, 1)';
      needle.setAttribute('transform', `rotate(${angle}, 100, 100)`);
    }

    // Animate number
    this._animateNumber('gauge-value', prob, 1);

    // Status badge
    const badge = document.getElementById('status-badge');
    if (badge) {
      badge.classList.remove('status-safe', 'status-warning', 'status-danger');
      if (prob < 20) {
        badge.textContent = 'AMAN';
        badge.classList.add('status-safe');
      } else if (prob < 60) {
        badge.textContent = 'WASPADA';
        badge.classList.add('status-warning');
      } else {
        badge.textContent = 'KRITIS';
        badge.classList.add('status-danger');
      }
    }
  }

  // ═══════════════════ STATS CARDS ═══════════════════

  _updateStatsCards(result) {
    // Min distance
    const distEl = document.getElementById('stat-distance-value');
    const distAuEl = document.getElementById('stat-distance-au');
    if (distEl && result.min_distance_km !== undefined) {
      distEl.textContent = this._formatDistance(result.min_distance_km);
      if (distAuEl) {
        const au = result.min_distance_km / 1.496e8;
        distAuEl.textContent = `≈ ${au.toFixed(4)} AU`;
      }
    }

    // Color code distance card
    const distCard = document.getElementById('stat-distance');
    if (distCard && result.min_distance_km !== undefined) {
      distCard.classList.remove('stat-card--safe', 'stat-card--warning', 'stat-card--danger');
      if (result.min_distance_km > 1e6) {
        distCard.classList.add('stat-card--safe');
      } else if (result.min_distance_km > 1e5) {
        distCard.classList.add('stat-card--warning');
      } else {
        distCard.classList.add('stat-card--danger');
      }
    }

    // Orbital energy
    const energyEl = document.getElementById('stat-energy-value');
    if (energyEl && result.orbital_energy !== undefined) {
      const e = result.orbital_energy;
      if (Math.abs(e) > 1e6) {
        energyEl.textContent = (e / 1e6).toFixed(2) + ' M';
      } else if (Math.abs(e) > 1e3) {
        energyEl.textContent = (e / 1e3).toFixed(2) + ' K';
      } else {
        energyEl.textContent = e.toFixed(2);
      }
    }

    // Impact status
    const statusEl = document.getElementById('stat-status-value');
    const statusDetail = document.getElementById('stat-status-detail');
    const statusCard = document.getElementById('stat-status');
    if (statusEl) {
      statusCard?.classList.remove('stat-card--safe', 'stat-card--warning', 'stat-card--danger');
      if (result.impact) {
        statusEl.textContent = 'IMPACT';
        statusEl.style.color = 'var(--color-danger)';
        statusCard?.classList.add('stat-card--danger');
        if (statusDetail) statusDetail.textContent = 'Tabrakan terdeteksi!';
      } else if (result.min_distance_km !== undefined && result.min_distance_km < 1e5) {
        statusEl.textContent = 'DEKAT';
        statusEl.style.color = 'var(--color-warning)';
        statusCard?.classList.add('stat-card--warning');
        if (statusDetail) statusDetail.textContent = 'Near-miss asteroid';
      } else {
        statusEl.textContent = 'AMAN';
        statusEl.style.color = 'var(--color-safe)';
        statusCard?.classList.add('stat-card--safe');
        if (statusDetail) statusDetail.textContent = 'Tidak ada ancaman';
      }
    }
  }

  // ═══════════════════ HISTOGRAM ═══════════════════

  _updateHistogram(minDistances) {
    const container = document.getElementById('histogram-chart');
    if (!container) return;

    // Clear
    container.innerHTML = '';

    if (!minDistances || minDistances.length === 0) return;

    // Create bins
    const sorted = [...minDistances].sort((a, b) => a - b);
    const min = sorted[0];
    const max = sorted[sorted.length - 1];
    const nBins = Math.min(25, Math.max(8, Math.ceil(Math.sqrt(sorted.length))));
    const binWidth = (max - min) / nBins || 1;

    const bins = new Array(nBins).fill(0);
    for (const d of sorted) {
      const idx = Math.min(nBins - 1, Math.floor((d - min) / binWidth));
      bins[idx]++;
    }

    const maxCount = Math.max(...bins);

    // Create DOM bars
    for (let i = 0; i < nBins; i++) {
      const bar = document.createElement('div');
      bar.className = 'histogram-bar';
      const height = maxCount > 0 ? (bins[i] / maxCount) * 100 : 0;
      bar.style.height = `${height}%`;

      // Color based on distance: near=red, far=teal
      const t = i / (nBins - 1);
      const r = Math.round(255 * (1 - t) + 78 * t);
      const g = Math.round(107 * (1 - t) + 205 * t);
      const b = Math.round(107 * (1 - t) + 196 * t);
      bar.style.backgroundColor = `rgb(${r}, ${g}, ${b})`;
      bar.style.boxShadow = `0 0 8px rgba(${r}, ${g}, ${b}, 0.3)`;

      // Tooltip
      const binStart = min + i * binWidth;
      const binEnd = binStart + binWidth;
      bar.title = `${this._formatDistance(binStart)} – ${this._formatDistance(binEnd)}\nCount: ${bins[i]}`;

      // Animate in
      bar.style.animationDelay = `${i * 30}ms`;

      container.appendChild(bar);
    }

    // Axis labels
    const midLabel = document.getElementById('histogram-mid-label');
    const maxLabel = document.getElementById('histogram-max-label');
    if (midLabel) midLabel.textContent = this._formatDistance((min + max) / 2);
    if (maxLabel) maxLabel.textContent = this._formatDistance(max);
  }

  // ═══════════════════ DEVIATION CHART ═══════════════════

  _updateDeviationChart(deviationKm, timeDays, thresholdDay) {
    const svg = document.getElementById('deviation-svg');
    if (!svg || !deviationKm || !timeDays) return;

    const width = 600;
    const height = 200;
    const padding = { top: 15, right: 60, bottom: 25, left: 10 };
    const plotW = width - padding.left - padding.right;
    const plotH = height - padding.top - padding.bottom;

    const maxTime = Math.max(...timeDays);
    const maxDev = Math.max(...deviationKm, 10000); // at least 10,000 km

    // Use log scale for deviation
    const logMax = Math.log10(Math.max(maxDev, 1));
    const logMin = 0; // log10(1) = 0

    // Build polyline points
    const points = [];
    const areaPoints = [];

    for (let i = 0; i < timeDays.length; i++) {
      const x = padding.left + (timeDays[i] / maxTime) * plotW;
      const logVal = deviationKm[i] > 0 ? Math.log10(deviationKm[i]) : 0;
      const y = padding.top + plotH - ((logVal - logMin) / (logMax - logMin)) * plotH;
      points.push(`${x.toFixed(1)},${y.toFixed(1)}`);
      areaPoints.push(`${x.toFixed(1)},${y.toFixed(1)}`);
    }

    // Area (closed polygon)
    const lastX = padding.left + plotW;
    const baseY = padding.top + plotH;
    const fullArea = [...areaPoints, `${lastX},${baseY}`, `${padding.left},${baseY}`].join(' ');

    const polyline = document.getElementById('deviation-line');
    const area = document.getElementById('deviation-area');
    if (polyline) polyline.setAttribute('points', points.join(' '));
    if (area) area.setAttribute('points', fullArea);

    // Threshold line at 10,000 km
    const threshLog = Math.log10(10000);
    const threshY = padding.top + plotH - ((threshLog - logMin) / (logMax - logMin)) * plotH;
    const threshLine = document.getElementById('deviation-threshold');
    const threshLabel = document.getElementById('deviation-threshold-label');
    if (threshLine) {
      threshLine.setAttribute('y1', threshY.toFixed(1));
      threshLine.setAttribute('y2', threshY.toFixed(1));
      threshLine.setAttribute('x1', padding.left.toString());
      threshLine.setAttribute('x2', (padding.left + plotW).toString());
    }
    if (threshLabel) {
      threshLabel.setAttribute('x', (padding.left + plotW + 5).toString());
      threshLabel.setAttribute('y', (threshY + 4).toString());
    }
  }

  // ═══════════════════ UI HELPERS ═══════════════════

  _setMode(mode) {
    this.state.currentMode = mode;
    const indicator = document.getElementById('mode-indicator');
    if (indicator) {
      const label = indicator.querySelector('.mode-label');
      const dot = indicator.querySelector('.mode-dot');
      if (label) label.textContent = mode.toUpperCase();
      if (dot) {
        dot.classList.remove('mode-dot--trajectory', 'mode-dot--anomaly', 'mode-dot--montecarlo');
        dot.classList.add(`mode-dot--${mode}`);
      }
    }

    // Hide/show result cards
    const histCard = document.getElementById('histogram-card');
    const devCard = document.getElementById('deviation-card');
    if (mode !== 'montecarlo' && histCard) histCard.style.display = 'none';
    if (mode !== 'anomaly' && devCard) devCard.style.display = 'none';
  }

  _showLoading() {
    const el = document.getElementById('canvas-loading');
    if (el) el.classList.add('active');
  }

  _hideLoading() {
    const el = document.getElementById('canvas-loading');
    if (el) el.classList.remove('active');
  }

  _showProgress(completed, total, impacts) {
    const container = document.getElementById('progress-container');
    if (container) container.classList.add('active');

    const fill = document.getElementById('progress-fill');
    if (fill) {
      const pct = total > 0 ? (completed / total) * 100 : 0;
      fill.style.width = `${pct}%`;
    }

    const count = document.getElementById('progress-count');
    if (count) count.textContent = `${completed} / ${total}`;

    const impactsEl = document.getElementById('progress-impacts');
    if (impactsEl) impactsEl.textContent = `Impact terdeteksi: ${impacts}`;
  }

  _hideProgress() {
    const container = document.getElementById('progress-container');
    if (container) container.classList.remove('active');
  }

  _setButtonState(btnId, disabled) {
    const btn = document.getElementById(btnId);
    if (btn) {
      btn.disabled = disabled;
      if (disabled) {
        btn.classList.add('btn--loading');
      } else {
        btn.classList.remove('btn--loading');
      }
    }
  }

  _showError(message) {
    // Simple error toast — could be enhanced
    console.error(message);
    const existing = document.querySelector('.error-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'error-toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('fade-out');
      setTimeout(() => toast.remove(), 400);
    }, 4000);
  }

  _animateNumber(elementId, target, decimals = 1) {
    const el = document.getElementById(elementId);
    if (!el) return;

    const start = parseFloat(el.textContent) || 0;
    const duration = 800;
    const startTime = performance.now();

    const animate = (now) => {
      const elapsed = now - startTime;
      const progress = Math.min(1, elapsed / duration);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = start + (target - start) * eased;
      el.textContent = current.toFixed(decimals);

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };
    requestAnimationFrame(animate);
  }

  _formatDistance(km) {
    if (km === undefined || km === null) return '—';
    if (km >= 1e9) return (km / 1e9).toFixed(2) + ' B km';
    if (km >= 1e6) return (km / 1e6).toFixed(2) + ' M km';
    if (km >= 1e3) return (km / 1e3).toFixed(1) + 'K km';
    return km.toFixed(0) + ' km';
  }
}

// ═══════════════════ BOOTSTRAP ═══════════════════

document.addEventListener('DOMContentLoaded', () => {
  const app = new SkjoldApp();
  app.init().catch(err => {
    console.error('App initialization failed:', err);
  });
});
