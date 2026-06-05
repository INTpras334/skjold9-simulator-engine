/**
 * Skjold-9 API Client
 * Handles all communication with the FastAPI backend.
 * Uses fetch() for REST and ReadableStream for SSE (POST).
 */

class SkjoldAPI {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
  }

  /**
   * GET /api/defaults
   * Returns default parameter values from the backend.
   */
  async getDefaults() {
    const res = await fetch(`${this.baseUrl}/api/defaults`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) {
      throw new Error(`Failed to fetch defaults: ${res.status} ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * POST /api/simulate/trajectory
   * @param {Object} params - { r_x, r_y, v_x, v_y, anomaly, anomaly_strength }
   * @returns {Promise<Object>} TrajectoryResult
   */
  async simulateTrajectory(params) {
    const res = await fetch(`${this.baseUrl}/api/simulate/trajectory`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        r_x: params.r_x,
        r_y: params.r_y,
        v_x: params.v_x,
        v_y: params.v_y,
        anomaly: params.anomaly,
        anomaly_strength: params.anomaly_strength,
      }),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Trajectory simulation failed: ${res.status} — ${text}`);
    }
    return res.json();
  }

  /**
   * POST /api/simulate/anomaly
   * @param {Object} params - { r_x, r_y, v_x, v_y, anomaly_strength }
   * @returns {Promise<Object>} AnomalyResult
   */
  async simulateAnomaly(params) {
    const res = await fetch(`${this.baseUrl}/api/simulate/anomaly`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        r_x: params.r_x,
        r_y: params.r_y,
        v_x: params.v_x,
        v_y: params.v_y,
        anomaly_strength: params.anomaly_strength,
      }),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Anomaly simulation failed: ${res.status} — ${text}`);
    }
    return res.json();
  }

  /**
   * POST /api/simulate/monte-carlo (SSE stream)
   * EventSource only supports GET, so we use fetch + ReadableStream.
   *
   * SSE format:
   *   event: progress\ndata: {"completed":10,"total":100,"impacts_so_far":2}\n\n
   *   event: result\ndata: {...}\n\n
   *
   * @param {Object} params - { r_x, r_y, v_x, v_y, n_sims, sigma_pos_au, sigma_vel_ms, anomaly, anomaly_strength }
   * @param {Object} callbacks - { onProgress, onResult, onError }
   * @returns {AbortController} controller to cancel the stream
   */
  streamMonteCarlo(params, { onProgress, onResult, onError }) {
    const controller = new AbortController();

    const doStream = async () => {
      try {
        const res = await fetch(`${this.baseUrl}/api/simulate/monte-carlo`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          },
          body: JSON.stringify({
            r_x: params.r_x,
            r_y: params.r_y,
            v_x: params.v_x,
            v_y: params.v_y,
            n_sims: params.n_sims,
            sigma_pos_au: params.sigma_pos_au,
            sigma_vel_ms: params.sigma_vel_ms,
            anomaly: params.anomaly,
            anomaly_strength: params.anomaly_strength,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const text = await res.text();
          throw new Error(`Monte Carlo stream failed: ${res.status} — ${text}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE events from buffer
          const events = this._parseSSE(buffer);
          buffer = events.remaining;

          for (const evt of events.parsed) {
            if (evt.event === 'progress' && onProgress) {
              onProgress(evt.data);
            } else if (evt.event === 'result' && onResult) {
              onResult(evt.data);
            } else if (evt.event === 'error' && onError) {
              onError(new Error(evt.data.message || 'Stream error'));
            }
          }
        }
      } catch (err) {
        if (err.name === 'AbortError') {
          // User cancelled — not an error
          return;
        }
        if (onError) {
          onError(err);
        }
      }
    };

    doStream();
    return controller;
  }

  /**
   * Parse SSE text buffer into structured events.
   * Returns { parsed: [{event, data}], remaining: string }
   */
  _parseSSE(buffer) {
    const parsed = [];
    const blocks = buffer.split('\n\n');

    // Last block might be incomplete
    const remaining = blocks.pop() || '';

    for (const block of blocks) {
      if (!block.trim()) continue;

      let eventType = 'message';
      let dataLines = [];

      const lines = block.split('\n');
      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          dataLines.push(line.slice(5).trim());
        }
      }

      if (dataLines.length > 0) {
        const raw = dataLines.join('\n');
        let data;
        try {
          data = JSON.parse(raw);
        } catch {
          data = { raw };
        }
        parsed.push({ event: eventType, data });
      }
    }

    return { parsed, remaining };
  }
}

// Global singleton
const api = new SkjoldAPI();
