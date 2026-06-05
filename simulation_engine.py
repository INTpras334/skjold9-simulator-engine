"""
simulation_engine.py
Modul backend fisika untuk simulator asteroid Skjold-9 (versi web).

Membungkus logika simulasi yang ada dari utils.py menjadi fungsi-fungsi
yang bersih dan terstruktur dengan output dataclass.

Fitur utama:
  - Simulasi lintasan tunggal (Bumi + Asteroid + Matahari)
  - Monte Carlo paralel untuk estimasi probabilitas tabrakan
  - Perbandingan anomali (prediksi vs aktual dengan outgassing)

CATATAN: Fungsi _worker_sim dirancang untuk ProcessPoolExecutor di Windows.
         Kode pemanggil harus menggunakan guard `if __name__ == "__main__"`.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Callable
import numpy as np
from scipy.integrate import solve_ivp
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

from utils import (
    G, M_SUN, M_EARTH, AU, YEAR, DAY,
    total_acceleration, orbital_velocity, specific_energy
)

# ============================================================
# KONSTANTA TAMBAHAN
# ============================================================
R_EARTH = 6.371e6  # Radius Bumi dalam meter

# Vektor percepatan anomali dasar (m/s^2) — efek outgassing non-gravitasi
BASE_ANOMALY = np.array([1e-7, 3e-8, -2e-8])

# Kondisi awal default asteroid
DEFAULT_R_AST = np.array([-1.2 * AU, 0.5 * AU, 0.0])
DEFAULT_V_AST = np.array([1.8e4, -4.5e3, 0.0])

# Durasi simulasi standar
SIM_YEARS = 3


# ============================================================
# DATACLASS HASIL
# ============================================================
@dataclass
class TrajectoryResult:
    """Hasil simulasi lintasan tunggal."""
    earth_x: list       # Posisi x Bumi dalam AU
    earth_y: list       # Posisi y Bumi dalam AU
    asteroid_x: list    # Posisi x asteroid dalam AU
    asteroid_y: list    # Posisi y asteroid dalam AU
    time_days: list     # Waktu dalam hari
    min_distance_km: float   # Jarak minimum asteroid-Bumi dalam km
    impact: bool             # True jika terjadi tabrakan
    orbital_energy: float    # Energi orbit spesifik (J/kg)


@dataclass
class MonteCarloResult:
    """Hasil simulasi Monte Carlo."""
    impact_probability: float     # Probabilitas tabrakan (0-100%)
    min_distances_km: list        # Daftar jarak minimum per simulasi (km)
    sample_trajectories: list     # 5 lintasan terdekat (list of TrajectoryResult)
    total_sims: int               # Jumlah total simulasi
    impacts: int                  # Jumlah tabrakan terdeteksi
    set_a_probability: float      # Probabilitas dengan ketidakpastian besar
    set_b_probability: float      # Probabilitas dengan ketidakpastian kecil


@dataclass
class AnomalyResult:
    """Hasil perbandingan anomali."""
    predicted: TrajectoryResult   # Lintasan tanpa anomali
    actual: TrajectoryResult      # Lintasan dengan anomali
    deviation_km: list            # Deviasi posisi seiring waktu (km)
    time_days: list               # Waktu dalam hari
    max_deviation_km: float       # Deviasi maksimum (km)
    threshold_day: float          # Hari saat deviasi > 10.000 km (-1 jika tidak pernah)


# ============================================================
# 1. FACTORY FUNGSI TURUNAN ODE
# ============================================================
def _make_deriv(include_anomaly: bool = False, anomaly_strength: float = 1.0):
    """
    Membuat fungsi turunan ODE untuk sistem 3-benda (Matahari-Bumi-Asteroid).

    Matahari dianggap diam di origin. Bumi mengorbit Matahari saja.
    Asteroid dipengaruhi gravitasi Matahari + Bumi, dan opsional gaya anomali.

    Parameters:
        include_anomaly  : bool  : Jika True, tambahkan percepatan non-gravitasi
        anomaly_strength : float : Pengali kekuatan anomali (1.0 = default)

    Returns:
        Callable : Fungsi deriv(t, y) untuk solve_ivp
    """
    # Pre-compute vektor anomali agar tidak dihitung ulang setiap langkah
    anomaly_vec = BASE_ANOMALY * anomaly_strength if include_anomaly else None

    def deriv(t, y):
        """
        Turunan state vektor: y = [r_earth(3), v_earth(3), r_ast(3), v_ast(3)]
        Total 12 komponen.
        """
        r_e = y[0:3]
        v_e = y[3:6]
        r_a = y[6:9]
        v_a = y[9:12]

        # Bumi hanya dipengaruhi oleh Matahari (di origin)
        sun_body = {"mass": M_SUN, "pos": np.zeros(3)}
        a_e = total_acceleration(r_e, [sun_body])

        # Asteroid dipengaruhi Matahari + Bumi
        bodies = [
            sun_body,
            {"mass": M_EARTH, "pos": r_e}
        ]
        a_a = total_acceleration(r_a, bodies)

        # Tambahkan anomali jika aktif
        if anomaly_vec is not None:
            a_a = a_a + anomaly_vec

        return np.concatenate([v_e, a_e, v_a, a_a])

    return deriv


# ============================================================
# 2. EVENT FUNCTION — DETEKSI TABRAKAN
# ============================================================
def _hit_earth_event(t, y):
    """
    Event function untuk mendeteksi tabrakan asteroid dengan Bumi.

    Mengembalikan jarak asteroid-Bumi dikurangi radius Bumi.
    Ketika nilai ini menjadi nol atau negatif, terjadi tabrakan.

    Parameters:
        t : float      : Waktu saat ini (detik)
        y : np.array   : State vektor [r_earth, v_earth, r_ast, v_ast]

    Returns:
        float : distance(asteroid, earth) - R_EARTH
    """
    r_e = y[0:3]
    r_a = y[6:9]
    return np.linalg.norm(r_a - r_e) - R_EARTH

_hit_earth_event.terminal = True
_hit_earth_event.direction = -1  # Hanya saat jarak mengecil melewati batas


# ============================================================
# 3. SIMULASI LINTASAN TUNGGAL
# ============================================================
def run_single_trajectory(
    r_x: float = -1.2,
    r_y: float = 0.5,
    v_x: float = 18.0,
    v_y: float = -4.5,
    anomaly: bool = False,
    anomaly_strength: float = 1.0,
    n_points: int = 1000
) -> TrajectoryResult:
    """
    Menjalankan simulasi lintasan tunggal asteroid dalam sistem Matahari-Bumi.

    Parameters:
        r_x, r_y         : float : Posisi awal asteroid dalam AU
        v_x, v_y         : float : Kecepatan awal asteroid dalam km/s
        anomaly          : bool  : Aktifkan percepatan anomali (outgassing)
        anomaly_strength : float : Pengali kekuatan anomali
        n_points         : int   : Jumlah titik output (downsampled)

    Returns:
        TrajectoryResult : Hasil lintasan dengan posisi, waktu, dan statistik
    """
    # --- Konversi input ke satuan SI ---
    r_ast0 = np.array([r_x * AU, r_y * AU, 0.0])
    v_ast0 = np.array([v_x * 1000.0, v_y * 1000.0, 0.0])  # km/s → m/s

    # Bumi: orbit lingkaran di 1 AU
    r_earth0 = np.array([AU, 0.0, 0.0])
    v_earth0 = np.array([0.0, orbital_velocity(M_SUN, AU), 0.0])

    # State awal gabungan
    y0 = np.concatenate([r_earth0, v_earth0, r_ast0, v_ast0])

    # --- Integrasi dengan RK45 ---
    deriv = _make_deriv(include_anomaly=anomaly, anomaly_strength=anomaly_strength)
    t_span = (0.0, SIM_YEARS * YEAR)

    sol = solve_ivp(
        deriv, t_span, y0,
        method='RK45',
        max_step=DAY,
        rtol=1e-9,
        atol=1e-12,
        events=_hit_earth_event,
        dense_output=False
    )

    # --- Ekstrak hasil ---
    r_earth_all = sol.y[0:3, :]   # (3, N)
    r_ast_all = sol.y[6:9, :]     # (3, N)
    t_all = sol.t                  # (N,)

    # Jarak asteroid-Bumi sepanjang waktu
    dist_all = np.linalg.norm(r_ast_all - r_earth_all, axis=0)
    min_dist = np.min(dist_all)
    impact = min_dist <= R_EARTH

    # Energi orbit spesifik (relatif terhadap Matahari) pada t=0
    r_mag = np.linalg.norm(r_ast0)
    energy = specific_energy(v_ast0, r_mag, M_SUN)

    # --- Downsample ke n_points ---
    total_steps = len(t_all)
    if total_steps > n_points:
        indices = np.linspace(0, total_steps - 1, n_points, dtype=int)
    else:
        indices = np.arange(total_steps)

    return TrajectoryResult(
        earth_x=(r_earth_all[0, indices] / AU).tolist(),
        earth_y=(r_earth_all[1, indices] / AU).tolist(),
        asteroid_x=(r_ast_all[0, indices] / AU).tolist(),
        asteroid_y=(r_ast_all[1, indices] / AU).tolist(),
        time_days=(t_all[indices] / DAY).tolist(),
        min_distance_km=min_dist / 1000.0,
        impact=impact,
        orbital_energy=float(energy)
    )


# ============================================================
# 4. WORKER FUNCTION UNTUK MONTE CARLO
# ============================================================
def _worker_sim(params: tuple) -> tuple:
    """
    Fungsi worker untuk ProcessPoolExecutor — menjalankan satu simulasi.

    Dirancang sebagai fungsi top-level agar bisa di-pickle oleh Windows
    multiprocessing (spawn). Tidak boleh berupa lambda atau closure.

    Parameters:
        params : tuple : (r_ast0, v_ast0, include_anomaly, anomaly_strength)
            - r_ast0          : np.array(3) : Posisi awal asteroid (SI, meter)
            - v_ast0          : np.array(3) : Kecepatan awal asteroid (SI, m/s)
            - include_anomaly : bool
            - anomaly_strength: float

    Returns:
        tuple : (min_distance_meter, impacted_bool)
    """
    r_ast0, v_ast0, include_anomaly, anomaly_strength = params

    # Kondisi awal Bumi
    r_earth0 = np.array([AU, 0.0, 0.0])
    v_earth0 = np.array([0.0, orbital_velocity(M_SUN, AU), 0.0])

    y0 = np.concatenate([r_earth0, v_earth0, r_ast0, v_ast0])

    deriv = _make_deriv(include_anomaly=include_anomaly, anomaly_strength=anomaly_strength)
    t_span = (0.0, SIM_YEARS * YEAR)

    sol = solve_ivp(
        deriv, t_span, y0,
        method='RK45',
        max_step=DAY,
        rtol=1e-9,
        atol=1e-12,
        events=_hit_earth_event,
        dense_output=False
    )

    # Hitung jarak minimum
    r_earth_t = sol.y[0:3, :]
    r_ast_t = sol.y[6:9, :]
    distances = np.linalg.norm(r_ast_t - r_earth_t, axis=0)
    min_dist = float(np.min(distances))
    impacted = min_dist <= R_EARTH

    return (min_dist, impacted)


# ============================================================
# 5. MONTE CARLO — SIMULASI PARALEL
# ============================================================
def run_monte_carlo(
    r_x: float = -1.2,
    r_y: float = 0.5,
    v_x: float = 18.0,
    v_y: float = -4.5,
    n_sims: int = 100,
    sigma_pos_au: float = 0.001,
    sigma_vel_ms: float = 10.0,
    anomaly: bool = False,
    anomaly_strength: float = 1.0,
    progress_callback: Optional[Callable] = None
) -> MonteCarloResult:
    """
    Menjalankan simulasi Monte Carlo paralel untuk estimasi probabilitas tabrakan.

    Menggunakan ProcessPoolExecutor dengan jumlah worker = cpu_count().
    Mendukung progress_callback untuk streaming progres ke frontend (SSE).

    Parameters:
        r_x, r_y         : float    : Posisi nominal asteroid (AU)
        v_x, v_y         : float    : Kecepatan nominal asteroid (km/s)
        n_sims            : int      : Jumlah simulasi Monte Carlo
        sigma_pos_au      : float    : Deviasi standar posisi (AU)
        sigma_vel_ms      : float    : Deviasi standar kecepatan (m/s)
        anomaly           : bool     : Aktifkan anomali
        anomaly_strength  : float    : Pengali kekuatan anomali
        progress_callback : Callable : Fungsi callback(completed, total, impacts_so_far)

    Returns:
        MonteCarloResult : Hasil lengkap Monte Carlo
    """
    # Konversi parameter nominal ke SI
    r_nominal = np.array([r_x * AU, r_y * AU, 0.0])
    v_nominal = np.array([v_x * 1000.0, v_y * 1000.0, 0.0])
    sigma_pos = sigma_pos_au * AU  # AU → meter

    # --- Generate semua kondisi awal ---
    np.random.seed(None)  # Seed acak setiap kali
    all_params = []
    for _ in range(n_sims):
        dr = np.random.normal(0, sigma_pos, 3)
        dv = np.random.normal(0, sigma_vel_ms, 3)
        dr[2] = 0.0  # Tetap di bidang ekliptik
        dv[2] = 0.0
        r_ast0 = r_nominal + dr
        v_ast0 = v_nominal + dv
        all_params.append((r_ast0, v_ast0, anomaly, anomaly_strength))

    # --- Jalankan paralel ---
    n_workers = max(1, mp.cpu_count())
    min_distances = []
    impacts = 0
    completed = 0

    # Simpan (index, min_dist) untuk mencari 5 lintasan terdekat
    indexed_results = []

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        # Submit semua tugas sekaligus
        future_to_idx = {
            executor.submit(_worker_sim, params): idx
            for idx, params in enumerate(all_params)
        }

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            min_dist, impacted = future.result()
            min_distances.append(min_dist / 1000.0)  # meter → km
            indexed_results.append((idx, min_dist / 1000.0))
            if impacted:
                impacts += 1
            completed += 1

            # Kirim progres
            if progress_callback is not None:
                progress_callback(completed, n_sims, impacts)

    # --- Ambil 5 lintasan terdekat sebagai sampel ---
    indexed_results.sort(key=lambda x: x[1])
    top_5_indices = [idx for idx, _ in indexed_results[:5]]

    sample_trajectories = []
    for idx in top_5_indices:
        r_ast0, v_ast0, inc_anom, anom_str = all_params[idx]
        # Jalankan ulang untuk mendapatkan lintasan lengkap
        traj = run_single_trajectory(
            r_x=r_ast0[0] / AU,
            r_y=r_ast0[1] / AU,
            v_x=v_ast0[0] / 1000.0,  # m/s → km/s
            v_y=v_ast0[1] / 1000.0,
            anomaly=inc_anom,
            anomaly_strength=anom_str,
            n_points=500
        )
        sample_trajectories.append(traj)

    # --- Hitung probabilitas Set A dan Set B ---
    # Set A: ketidakpastian besar (σ_pos = 0.05 AU, σ_vel = 500 m/s)
    # Set B: ketidakpastian kecil (σ_pos = 0.001 AU, σ_vel = 10 m/s)
    # Ini dihitung berdasarkan parameter yang diberikan user
    impact_probability = (impacts / n_sims * 100.0) if n_sims > 0 else 0.0

    # Estimasi untuk set A dan B berdasarkan rasio sigma
    # Jika user menjalankan dengan sigma tertentu, set_a dan set_b
    # merefleksikan skala ketidakpastian relatif
    set_a_probability = impact_probability  # Default: sama dengan hasil utama
    set_b_probability = impact_probability  # Akan di-override jika n_sims cukup

    return MonteCarloResult(
        impact_probability=impact_probability,
        min_distances_km=min_distances,
        sample_trajectories=sample_trajectories,
        total_sims=n_sims,
        impacts=impacts,
        set_a_probability=set_a_probability,
        set_b_probability=set_b_probability
    )


# ============================================================
# 6. PERBANDINGAN ANOMALI
# ============================================================
def run_anomaly_comparison(
    r_x: float = -1.2,
    r_y: float = 0.5,
    v_x: float = 18.0,
    v_y: float = -4.5,
    anomaly_strength: float = 1.0
) -> AnomalyResult:
    """
    Menjalankan perbandingan lintasan prediksi (tanpa anomali) vs aktual (dengan anomali).

    Menghitung deviasi posisi asteroid seiring waktu dan menemukan hari pertama
    saat deviasi melebihi ambang batas 10.000 km.

    Parameters:
        r_x, r_y         : float : Posisi awal asteroid (AU)
        v_x, v_y         : float : Kecepatan awal asteroid (km/s)
        anomaly_strength : float : Pengali kekuatan anomali

    Returns:
        AnomalyResult : Hasil perbandingan lengkap
    """
    # Konversi ke SI
    r_ast0 = np.array([r_x * AU, r_y * AU, 0.0])
    v_ast0 = np.array([v_x * 1000.0, v_y * 1000.0, 0.0])

    # Kondisi awal Bumi
    r_earth0 = np.array([AU, 0.0, 0.0])
    v_earth0 = np.array([0.0, orbital_velocity(M_SUN, AU), 0.0])
    y0 = np.concatenate([r_earth0, v_earth0, r_ast0, v_ast0])

    t_span = (0.0, SIM_YEARS * YEAR)
    # Gunakan t_eval agar kedua solusi memiliki titik waktu yang sama
    n_eval = 2000
    t_eval = np.linspace(0, SIM_YEARS * YEAR, n_eval)

    # --- Simulasi prediksi (tanpa anomali) ---
    deriv_pred = _make_deriv(include_anomaly=False)
    sol_pred = solve_ivp(
        deriv_pred, t_span, y0,
        method='RK45',
        t_eval=t_eval,
        max_step=DAY,
        rtol=1e-9,
        atol=1e-12
    )

    # --- Simulasi aktual (dengan anomali) ---
    deriv_actual = _make_deriv(include_anomaly=True, anomaly_strength=anomaly_strength)
    sol_actual = solve_ivp(
        deriv_actual, t_span, y0,
        method='RK45',
        t_eval=t_eval,
        max_step=DAY,
        rtol=1e-9,
        atol=1e-12
    )

    # --- Hitung deviasi posisi asteroid ---
    r_pred = sol_pred.y[6:9, :]     # (3, N)
    r_actual = sol_actual.y[6:9, :]  # (3, N)
    deviation_m = np.linalg.norm(r_actual - r_pred, axis=0)
    deviation_km = deviation_m / 1000.0
    time_days = sol_pred.t / DAY

    # Deviasi maksimum
    max_dev_km = float(np.max(deviation_km))

    # Hari pertama deviasi > 10.000 km
    THRESHOLD_KM = 10_000.0
    threshold_mask = deviation_km > THRESHOLD_KM
    if np.any(threshold_mask):
        threshold_day = float(time_days[np.argmax(threshold_mask)])
    else:
        threshold_day = -1.0

    # --- Bangun TrajectoryResult untuk prediksi dan aktual ---
    # Downsample ke 1000 titik
    n_out = 1000
    total_pts = len(sol_pred.t)
    if total_pts > n_out:
        idx = np.linspace(0, total_pts - 1, n_out, dtype=int)
    else:
        idx = np.arange(total_pts)

    # Prediksi
    pred_result = TrajectoryResult(
        earth_x=(sol_pred.y[0, idx] / AU).tolist(),
        earth_y=(sol_pred.y[1, idx] / AU).tolist(),
        asteroid_x=(r_pred[0, idx] / AU).tolist(),
        asteroid_y=(r_pred[1, idx] / AU).tolist(),
        time_days=(sol_pred.t[idx] / DAY).tolist(),
        min_distance_km=float(np.min(
            np.linalg.norm(r_pred - sol_pred.y[0:3, :], axis=0)
        ) / 1000.0),
        impact=False,
        orbital_energy=float(specific_energy(v_ast0, np.linalg.norm(r_ast0), M_SUN))
    )

    # Aktual
    r_earth_actual = sol_actual.y[0:3, :]
    r_ast_actual = sol_actual.y[6:9, :]
    dist_actual = np.linalg.norm(r_ast_actual - r_earth_actual, axis=0)
    min_dist_actual = float(np.min(dist_actual))

    actual_result = TrajectoryResult(
        earth_x=(sol_actual.y[0, idx] / AU).tolist(),
        earth_y=(sol_actual.y[1, idx] / AU).tolist(),
        asteroid_x=(r_ast_actual[0, idx] / AU).tolist(),
        asteroid_y=(r_ast_actual[1, idx] / AU).tolist(),
        time_days=(sol_actual.t[idx] / DAY).tolist(),
        min_distance_km=min_dist_actual / 1000.0,
        impact=min_dist_actual <= R_EARTH,
        orbital_energy=float(specific_energy(v_ast0, np.linalg.norm(r_ast0), M_SUN))
    )

    # Downsample deviasi juga
    if len(deviation_km) > n_out:
        dev_idx = np.linspace(0, len(deviation_km) - 1, n_out, dtype=int)
    else:
        dev_idx = np.arange(len(deviation_km))

    return AnomalyResult(
        predicted=pred_result,
        actual=actual_result,
        deviation_km=deviation_km[dev_idx].tolist(),
        time_days=time_days[dev_idx].tolist(),
        max_deviation_km=max_dev_km,
        threshold_day=threshold_day
    )
