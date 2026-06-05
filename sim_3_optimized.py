"""
sim_3_optimized.py
Simulasi Monte Carlo Ultra-Cepat dengan Early Stopping & Multi-Processing.
"""

import os
import sys
os.environ['TCL_LIBRARY'] = r'D:\laragon\bin\python\python-3.13\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'D:\laragon\bin\python\python-3.13\tcl\tk8.6'

import matplotlib
matplotlib.use('TkAgg')

import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
from functools import partial

from utils import (
    G, M_SUN, M_EARTH, AU, YEAR, DAY,
    total_acceleration, orbital_velocity, distance
)

# ============================================================
# PARAMETER GLOBAL
# ============================================================
R_EARTH = 6.371e6
SIM_YEARS = 3

# Kondisi nominal asteroid
r_ast_nominal = np.array([-1.2 * AU, 0.5 * AU, 0.0])
v_ast_nominal = np.array([1.8e4, -4.5e3, 0.0])

# Ketidakpastian
SIGMA_POS_A = 0.05 * AU
SIGMA_VEL_A = 500.0
SIGMA_POS_B = 0.001 * AU
SIGMA_VEL_B = 10.0

# ============================================================
# 1. EARLY STOPPING EVENT
# ============================================================
def hit_earth_event(t, y):
    """Event: berhenti saat jarak asteroid ≤ radius Bumi."""
    r_earth = y[0:3]
    r_ast = y[6:9]
    return np.linalg.norm(r_ast - r_earth) - R_EARTH

hit_earth_event.terminal = True   # Hentikan integrasi saat tercapai
hit_earth_event.direction = -1     # Hanya saat mengecil (menabrak)

# ============================================================
# 2. FUNGSI SIMULASI SATU SKENARIO (DENGAN EARLY STOPPING)
# ============================================================
def run_single_sim(r_ast0, v_ast0, include_anomaly=False):
    """Simulasi satu skenario. Mengembalikan jarak minimum dan status tabrakan."""
    r_earth = np.array([AU, 0.0, 0.0])
    v_earth = np.array([0.0, orbital_velocity(M_SUN, AU), 0.0])
    y0 = np.concatenate([r_earth, v_earth, r_ast0, v_ast0])
    
    def deriv(t, y):
        r_e = y[0:3]; v_e = y[3:6]
        r_a = y[6:9]; v_a = y[9:12]
        
        # Bumi hanya oleh Matahari
        a_e = total_acceleration(r_e, [{"mass": M_SUN, "pos": np.zeros(3)}])
        # Asteroid oleh Matahari + Bumi
        a_a = total_acceleration(r_a, [
            {"mass": M_SUN, "pos": np.zeros(3)},
            {"mass": M_EARTH, "pos": r_e}
        ])
        
        if include_anomaly:
            ANOMALI_ACCEL = np.array([1e-7, 3e-8, -2e-8])
            a_a = a_a + ANOMALI_ACCEL
            
        return np.concatenate([v_e, a_e, v_a, a_a])
    
    # Integrasi dengan event early stopping
    sol = solve_ivp(deriv, (0, SIM_YEARS * YEAR), y0,
                    max_step=DAY, rtol=1e-9, atol=1e-12,
                    events=hit_earth_event)
    
    # Evaluasi jarak minimum
    r_ast = sol.y[6:9, :]
    r_earth_t = sol.y[0:3, :]
    distances = np.linalg.norm(r_ast - r_earth_t, axis=0)
    min_dist = np.min(distances)
    impacted = sol.t_events[0].size > 0  # True jika event terpicu
    
    return min_dist, impacted

# ============================================================
# 3. WRAPPER UNTUK MULTI-PROCESSING (Satu skenario)
# ============================================================
def worker_sim(params):
    """Fungsi yang dipanggil worker pool. params = (r_ast0, v_ast0, include_anomaly)"""
    r_ast0, v_ast0, include_anomaly = params
    min_dist, impacted = run_single_sim(r_ast0, v_ast0, include_anomaly)
    return min_dist, impacted

# ============================================================
# 4. MONTE CARLO PARALEL
# ============================================================
def monte_carlo_parallel(sigma_pos, sigma_vel, n_sim, include_anomaly=False):
    """
    Menjalankan n_sim simulasi secara paralel dengan variasi acak.
    """
    # Siapkan parameter untuk semua simulasi
    params_list = []
    for _ in range(n_sim):
        dr = np.random.normal(0, sigma_pos, 3)
        dv = np.random.normal(0, sigma_vel, 3)
        r0 = r_ast_nominal + dr
        v0 = v_ast_nominal + dv
        params_list.append((r0, v0, include_anomaly))
    
    # Eksekusi paralel
    min_dists = np.zeros(n_sim)
    impacts = 0
    
    with ProcessPoolExecutor(max_workers=mp.cpu_count()) as executor:
        futures = {executor.submit(worker_sim, p): i for i, p in enumerate(params_list)}
        for future in as_completed(futures):
            idx = futures[future]
            min_d, hit = future.result()
            min_dists[idx] = min_d
            if hit:
                impacts += 1
            # Progress opsional
            if (idx+1) % 100 == 0:
                print(f"  Selesai {idx+1}/{n_sim}")
    
    return min_dists, impacts

# ============================================================
# 5. EKSEKUSI UTAMA
# ============================================================
if __name__ == "__main__":
    N = 500  # Bisa dinaikkan hingga ribuan dengan aman
    
    print("="*60)
    print("MONTE CARLO OPTIMASI: EARLY STOPPING + MULTI-PROCESSING")
    print("="*60)
    
    import time
    t_start = time.time()
    
    print("\n[Set A] Ketidakpastian besar...")
    dists_A, hits_A = monte_carlo_parallel(SIGMA_POS_A, SIGMA_VEL_A, N)
    prob_A = hits_A / N * 100
    
    print("\n[Set B] Ketidakpastian kecil (akurat)...")
    dists_B, hits_B = monte_carlo_parallel(SIGMA_POS_B, SIGMA_VEL_B, N)
    prob_B = hits_B / N * 100
    
    t_end = time.time()
    print(f"\nWaktu total: {t_end - t_start:.2f} detik")
    
    # Output hasil
    print("\n" + "="*60)
    print("HASIL")
    print("="*60)
    print(f"Set A: {hits_A}/{N} tabrakan ({prob_A:.2f}%)")
    print(f"Set B: {hits_B}/{N} tabrakan ({prob_B:.2f}%)")
    
    # Plot (opsional)
    fig, ax = plt.subplots(1,1)
    ax.hist(dists_A/AU, bins=30, alpha=0.5, label='Set A')
    ax.hist(dists_B/AU, bins=30, alpha=0.5, label='Set B')
    ax.axvline(R_EARTH/AU, color='red', linestyle='--')
    ax.legend()
    ax.set_xlabel('Jarak Minimum (AU)')
    plt.show()