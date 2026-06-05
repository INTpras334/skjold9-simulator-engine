"""
server.py
Aplikasi FastAPI untuk backend web simulator asteroid Skjold-9.

Menyediakan endpoint REST API untuk simulasi lintasan, Monte Carlo,
dan perbandingan anomali. Monte Carlo menggunakan Server-Sent Events (SSE)
untuk streaming progres real-time ke frontend.

Endpoint:
    GET  /                          → Halaman utama (web/index.html)
    GET  /api/defaults              → Parameter default
    POST /api/simulate/trajectory   → Simulasi lintasan tunggal
    POST /api/simulate/anomaly      → Perbandingan anomali
    POST /api/simulate/monte-carlo  → Monte Carlo dengan SSE streaming
"""

import asyncio
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

from simulation_engine import (
    run_single_trajectory, run_monte_carlo, run_anomaly_comparison,
    TrajectoryResult, MonteCarloResult, AnomalyResult
)


# ============================================================
# KONFIGURASI APLIKASI
# ============================================================
app = FastAPI(
    title="Skjold-9 Asteroid Simulator",
    description="Backend API untuk simulator tabrakan asteroid Skjold-9",
    version="2.0.0"
)

# CORS middleware untuk development (akses dari localhost frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Direktori file statis
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"


# ============================================================
# MOUNT STATIC FILES
# ============================================================
# Mount direktori web/ untuk CSS, JS, dan aset statis lainnya
if WEB_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(WEB_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(WEB_DIR / "js")), name="js")


# ============================================================
# MODEL REQUEST (PYDANTIC)
# ============================================================
class TrajectoryParams(BaseModel):
    """Parameter untuk simulasi lintasan tunggal."""
    r_x: float = Field(-1.2, description="Posisi awal X asteroid (AU)")
    r_y: float = Field(0.5, description="Posisi awal Y asteroid (AU)")
    v_x: float = Field(18.0, description="Kecepatan awal X asteroid (km/s)")
    v_y: float = Field(-4.5, description="Kecepatan awal Y asteroid (km/s)")
    anomaly: bool = Field(False, description="Aktifkan anomali outgassing")
    anomaly_strength: float = Field(1.0, description="Pengali kekuatan anomali")


class AnomalyParams(BaseModel):
    """Parameter untuk perbandingan anomali."""
    r_x: float = Field(-1.2, description="Posisi awal X asteroid (AU)")
    r_y: float = Field(0.5, description="Posisi awal Y asteroid (AU)")
    v_x: float = Field(18.0, description="Kecepatan awal X asteroid (km/s)")
    v_y: float = Field(-4.5, description="Kecepatan awal Y asteroid (km/s)")
    anomaly_strength: float = Field(1.0, description="Pengali kekuatan anomali")


class MonteCarloParams(BaseModel):
    """Parameter untuk simulasi Monte Carlo."""
    r_x: float = Field(-1.2, description="Posisi awal X asteroid (AU)")
    r_y: float = Field(0.5, description="Posisi awal Y asteroid (AU)")
    v_x: float = Field(18.0, description="Kecepatan awal X asteroid (km/s)")
    v_y: float = Field(-4.5, description="Kecepatan awal Y asteroid (km/s)")
    n_sims: int = Field(100, ge=10, le=10000, description="Jumlah simulasi")
    sigma_pos_au: float = Field(0.001, ge=0.0001, le=1.0, description="Sigma posisi (AU)")
    sigma_vel_ms: float = Field(10.0, ge=0.1, le=5000.0, description="Sigma kecepatan (m/s)")
    anomaly: bool = Field(False, description="Aktifkan anomali outgassing")
    anomaly_strength: float = Field(1.0, description="Pengali kekuatan anomali")


# ============================================================
# UTILITAS SERIALISASI
# ============================================================
def dataclass_to_dict(obj) -> dict:
    """
    Mengkonversi dataclass (termasuk nested) ke dictionary JSON-serializable.

    Menangani konversi numpy array → list dan nested dataclass secara rekursif.

    Parameters:
        obj : dataclass instance

    Returns:
        dict : Dictionary yang bisa di-serialize ke JSON
    """
    if hasattr(obj, '__dataclass_fields__'):
        result = {}
        for key, value in asdict(obj).items():
            result[key] = _sanitize_value(value)
        return result
    return obj


def _sanitize_value(value):
    """
    Membersihkan nilai agar JSON-serializable.

    Mengkonversi numpy types ke Python native, dan menangani
    nested dict/list secara rekursif.
    """
    import numpy as np

    if isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_sanitize_value(v) for v in value]
    elif isinstance(value, np.ndarray):
        return value.tolist()
    elif isinstance(value, (np.float32, np.float64)):
        return float(value)
    elif isinstance(value, (np.int32, np.int64)):
        return int(value)
    elif isinstance(value, np.bool_):
        return bool(value)
    elif isinstance(value, float):
        # Tangani NaN dan Inf agar tidak crash JSON serializer
        if value != value:  # NaN check
            return None
        if value == float('inf') or value == float('-inf'):
            return None
        return value
    return value


# ============================================================
# ENDPOINT: HALAMAN UTAMA
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """
    Menyajikan halaman utama dari web/index.html.

    Jika file tidak ditemukan, mengembalikan halaman placeholder
    agar server tetap berjalan tanpa frontend.
    """
    index_path = WEB_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html")
    else:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head><title>Skjold-9 Simulator</title></head>
            <body style="background:#1a1a2e;color:#eee;font-family:sans-serif;
                         display:flex;align-items:center;justify-content:center;
                         height:100vh;margin:0;">
                <div style="text-align:center;">
                    <h1>🪨 Skjold-9 Asteroid Simulator</h1>
                    <p>API server berjalan. Frontend belum tersedia.</p>
                    <p>Buka <a href="/docs" style="color:#4fc3f7;">/docs</a>
                       untuk dokumentasi API interaktif.</p>
                </div>
            </body>
            </html>
            """,
            status_code=200
        )


# ============================================================
# ENDPOINT: DEFAULT PARAMETERS
# ============================================================
@app.get("/api/defaults")
async def get_defaults():
    """
    Mengembalikan parameter default untuk semua jenis simulasi.

    Berguna untuk frontend agar bisa mengisi form dengan nilai awal
    tanpa hardcode di sisi klien.
    """
    return {
        "trajectory": {
            "r_x": -1.2,
            "r_y": 0.5,
            "v_x": 18.0,
            "v_y": -4.5,
            "anomaly": False,
            "anomaly_strength": 1.0
        },
        "monte_carlo": {
            "r_x": -1.2,
            "r_y": 0.5,
            "v_x": 18.0,
            "v_y": -4.5,
            "n_sims": 100,
            "sigma_pos_au": 0.001,
            "sigma_vel_ms": 10.0,
            "anomaly": False,
            "anomaly_strength": 1.0
        },
        "anomaly": {
            "r_x": -1.2,
            "r_y": 0.5,
            "v_x": 18.0,
            "v_y": -4.5,
            "anomaly_strength": 1.0
        },
        "limits": {
            "r_range": [-3.0, 3.0],
            "v_range": [-50.0, 50.0],
            "n_sims_range": [10, 10000],
            "sigma_pos_range": [0.0001, 1.0],
            "sigma_vel_range": [0.1, 5000.0],
            "anomaly_strength_range": [0.1, 10.0]
        }
    }


# ============================================================
# ENDPOINT: SIMULASI LINTASAN TUNGGAL
# ============================================================
@app.post("/api/simulate/trajectory")
async def simulate_trajectory(params: TrajectoryParams):
    """
    Menjalankan simulasi lintasan tunggal asteroid.

    Simulasi berjalan di thread pool agar tidak memblokir event loop async.
    Menggunakan RK45 dengan durasi 3 tahun dan max_step = 1 hari.

    Parameters:
        params : TrajectoryParams : Parameter simulasi dari request body

    Returns:
        dict : TrajectoryResult dalam format JSON
    """
    result = await asyncio.to_thread(
        run_single_trajectory,
        r_x=params.r_x,
        r_y=params.r_y,
        v_x=params.v_x,
        v_y=params.v_y,
        anomaly=params.anomaly,
        anomaly_strength=params.anomaly_strength
    )
    return dataclass_to_dict(result)


# ============================================================
# ENDPOINT: PERBANDINGAN ANOMALI
# ============================================================
@app.post("/api/simulate/anomaly")
async def simulate_anomaly(params: AnomalyParams):
    """
    Menjalankan perbandingan lintasan prediksi vs aktual (dengan anomali).

    Menghitung deviasi posisi seiring waktu dan menemukan hari kritis
    saat deviasi melebihi 10.000 km.

    Parameters:
        params : AnomalyParams : Parameter simulasi dari request body

    Returns:
        dict : AnomalyResult dalam format JSON
    """
    result = await asyncio.to_thread(
        run_anomaly_comparison,
        r_x=params.r_x,
        r_y=params.r_y,
        v_x=params.v_x,
        v_y=params.v_y,
        anomaly_strength=params.anomaly_strength
    )
    return dataclass_to_dict(result)


# ============================================================
# ENDPOINT: MONTE CARLO DENGAN SSE STREAMING
# ============================================================
@app.post("/api/simulate/monte-carlo")
async def simulate_monte_carlo(params: MonteCarloParams):
    """
    Menjalankan simulasi Monte Carlo dengan streaming progres via SSE.

    Menggunakan Server-Sent Events (SSE) agar frontend bisa menampilkan
    progress bar real-time selama simulasi berjalan.

    Event yang dikirim:
        - "progress": {completed, total, impacts_so_far}
        - "result":   {MonteCarloResult lengkap}

    Parameters:
        params : MonteCarloParams : Parameter simulasi dari request body

    Returns:
        StreamingResponse : SSE stream dengan content-type text/event-stream
    """
    async def event_generator():
        """Generator SSE yang menjalankan Monte Carlo dan streaming progres."""
        queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def progress_callback(completed: int, total: int, impacts_so_far: int):
            """
            Callback yang dipanggil dari thread worker setiap simulasi selesai.
            Menggunakan call_soon_threadsafe untuk komunikasi thread-safe ke event loop.
            """
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "event": "progress",
                    "data": {
                        "completed": completed,
                        "total": total,
                        "impacts_so_far": impacts_so_far,
                        "percent": round(completed / total * 100, 1)
                    }
                }
            )

        # Jalankan simulasi Monte Carlo di thread terpisah
        task = asyncio.create_task(
            asyncio.to_thread(
                run_monte_carlo,
                r_x=params.r_x,
                r_y=params.r_y,
                v_x=params.v_x,
                v_y=params.v_y,
                n_sims=params.n_sims,
                sigma_pos_au=params.sigma_pos_au,
                sigma_vel_ms=params.sigma_vel_ms,
                anomaly=params.anomaly,
                anomaly_strength=params.anomaly_strength,
                progress_callback=progress_callback
            )
        )

        # Stream event progres selama task belum selesai
        while not task.done():
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=0.5)
                yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'])}\n\n"
            except asyncio.TimeoutError:
                # Kirim heartbeat agar koneksi tidak timeout
                yield f": heartbeat\n\n"
                continue

        # Flush sisa antrian progres yang belum terkirim
        while not queue.empty():
            try:
                msg = queue.get_nowait()
                yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'])}\n\n"
            except asyncio.QueueEmpty:
                break

        # Ambil hasil akhir dan kirim sebagai event "result"
        result = await task
        result_dict = dataclass_to_dict(result)
        yield f"event: result\ndata: {json.dumps(result_dict)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nonaktifkan buffering nginx jika ada
        }
    )


# ============================================================
# HEALTH CHECK
# ============================================================
@app.get("/api/health")
async def health_check():
    """Endpoint untuk memeriksa status server."""
    return {"status": "ok", "service": "skjold9-simulator"}


# ============================================================
# STARTUP EVENT
# ============================================================
@app.on_event("startup")
async def startup_event():
    """Log informasi saat server dimulai."""
    print("=" * 60)
    print("  [Skjold-9] Asteroid Simulator - Server Aktif")
    print("=" * 60)
    print(f"  Frontend: {'web/' if WEB_DIR.exists() else '(belum tersedia)'}")
    print(f"  API docs: http://localhost:8000/docs")
    print(f"  Health:   http://localhost:8000/api/health")
    print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
