"""
sim_3_monte_carlo_impact_prob.py
Simulasi Monte Carlo untuk menghitung probabilitas tabrakan asteroid dengan Bumi.
Membandingkan dua set parameter:
  - Set A: parameter awal dengan ketidakpastian besar (asumsi lama)
  - Set B: parameter yang lebih akurat (setelah koreksi data)
"""

import os
import sys
os.environ['TCL_LIBRARY'] = r'D:\laragon\bin\python\python-3.13\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'D:\laragon\bin\python\python-3.13\tcl\tk8.6'

import matplotlib
matplotlib.use('TkAgg')  # Kembalikan ke TkAgg karena Tcl/Tk sudah diperbaiki

import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from utils import (
    G, M_SUN, M_EARTH, AU, YEAR, DAY,
    total_acceleration, orbital_velocity, distance
)

# ============================================================
# PARAMETER SIMULASI
# ============================================================
R_EARTH = 6.371e6           # Radius Bumi (m) untuk deteksi tabrakan
N_SIMULATIONS = 500         # Jumlah simulasi per set (semakin besar semakin akurat)
SIM_YEARS = 3               # Durasi simulasi (tahun)

# ============================================================
# KONDISI AWAL NOMINAL ASTEROID
# ============================================================
# Posisi dan kecepatan referensi (sama seperti di sim_2)
r_ast_nominal = np.array([-1.2 * AU, 0.5 * AU, 0.0])
v_ast_nominal = np.array([1.8e4, -4.5e3, 0.0])

# ============================================================
# KETIDAKPASTIAN PARAMETER
# ============================================================
# Set A (asumsi lama): ketidakpastian besar
# Deviasi standar untuk posisi (meter) dan kecepatan (m/s)
SIGMA_POS_A = 0.05 * AU       # ±0.05 AU (~7,5 juta km)
SIGMA_VEL_A = 500.0           # ±500 m/s

# Set B (setelah koreksi): ketidakpastian kecil
SIGMA_POS_B = 0.001 * AU      # ±0.001 AU (~150.000 km)
SIGMA_VEL_B = 10.0            # ±10 m/s

# ============================================================
# FUNGSI SIMULASI SATU SKENARIO
# ============================================================
def run_single_sim(r_ast0, v_ast0, include_anomaly=False):
    """
    Menjalankan simulasi 3-benda dan mengembalikan jarak minimum asteroid ke Bumi.
    
    Parameters:
        r_ast0, v_ast0 : posisi dan kecepatan awal asteroid
        include_anomaly : jika True, tambahkan gaya non-gravitasi
    
    Returns:
        min_distance : jarak terdekat asteroid ke pusat Bumi (meter)
        trajectory   : (opsional) data lintasan
    """
    # Posisi dan kecepatan awal Bumi (orbit lingkaran)
    r_earth = np.array([AU, 0.0, 0.0])
    v_earth = np.array([0.0, orbital_velocity(M_SUN, AU), 0.0])
    
    # Gabung state
    y0 = np.concatenate([r_earth, v_earth, r_ast0, v_ast0])
    
    # Fungsi turunan
    def deriv(t, y):
        r_e = y[0:3]; v_e = y[3:6]
        r_a = y[6:9]; v_a = y[9:12]
        
        bodies = [
            {"mass": M_SUN,   "pos": np.zeros(3)},
            {"mass": M_EARTH, "pos": r_e}
        ]
        
        # Bumi hanya oleh Matahari
        a_e = total_acceleration(r_e, [bodies[0]])
        # Asteroid oleh Matahari + Bumi
        a_a = total_acceleration(r_a, bodies)
        
        if include_anomaly:
            # Tambah gaya non-gravitasi kecil
            ANOMALI_ACCEL = np.array([1e-7, 3e-8, -2e-8])
            a_a = a_a + ANOMALI_ACCEL
            
        return np.concatenate([v_e, a_e, v_a, a_a])
    
    # Integrasi dengan toleransi ketat
    sol = solve_ivp(deriv, (0, SIM_YEARS * YEAR), y0,
                    max_step=DAY, rtol=1e-9, atol=1e-12)
    
    # Hitung jarak asteroid ke Bumi di setiap waktu
    r_ast = sol.y[6:9, :]
    r_earth_t = sol.y[0:3, :]
    distances = np.linalg.norm(r_ast - r_earth_t, axis=0)
    min_dist = np.min(distances)
    
    return min_dist, sol

# ============================================================
# MONTE CARLO
# ============================================================
def monte_carlo(sigma_pos, sigma_vel, n_sim, include_anomaly=False):
    """
    Menjalankan n_sim simulasi dengan variasi acak pada kondisi awal.
    
    Returns:
        min_distances : array jarak minimum tiap simulasi
        impacts       : jumlah tabrakan (jarak < R_EARTH)
    """
    min_distances = np.zeros(n_sim)
    impacts = 0
    
    for i in range(n_sim):
        # Variasi acak
        dr = np.random.normal(0, sigma_pos, 3)
        dv = np.random.normal(0, sigma_vel, 3)
        
        r_ast0 = r_ast_nominal + dr
        v_ast0 = v_ast_nominal + dv
        
        min_dist, _ = run_single_sim(r_ast0, v_ast0, include_anomaly)
        min_distances[i] = min_dist
        
        if min_dist <= R_EARTH:
            impacts += 1
        
        # Progress bar sederhana
        if (i+1) % 50 == 0:
            print(f"  Simulasi {i+1}/{n_sim} selesai...")
    
    return min_distances, impacts

# ============================================================
# EKSEKUSI
# ============================================================
print("="*60)
print("SIMULASI MONTE CARLO PROBABILITAS TABRAKAN ASTEROID")
print("="*60)

print("\n[1/2] SET A: Ketidakpastian Besar (asumsi lama)")
print(f"  Sigma posisi: {SIGMA_POS_A/AU:.2f} AU")
print(f"  Sigma kecepatan: {SIGMA_VEL_A:.0f} m/s")
min_dists_A, impacts_A = monte_carlo(SIGMA_POS_A, SIGMA_VEL_A, N_SIMULATIONS)
prob_A = impacts_A / N_SIMULATIONS * 100

print("\n[2/2] SET B: Ketidakpastian Kecil (setelah koreksi data)")
print(f"  Sigma posisi: {SIGMA_POS_B/AU:.3f} AU")
print(f"  Sigma kecepatan: {SIGMA_VEL_B:.0f} m/s")
min_dists_B, impacts_B = monte_carlo(SIGMA_POS_B, SIGMA_VEL_B, N_SIMULATIONS)
prob_B = impacts_B / N_SIMULATIONS * 100

# ============================================================
# HASIL
# ============================================================
print("\n" + "="*60)
print("HASIL AKHIR")
print("="*60)
print(f"SET A (asumsi lama):")
print(f"  Tabrakan: {impacts_A}/{N_SIMULATIONS}")
print(f"  Probabilitas: {prob_A:.2f}%")
print(f"  Jarak minimum rata-rata: {np.mean(min_dists_A)/1000:.0f} km")
print(f"  Jarak minimum terkecil:  {np.min(min_dists_A)/1000:.0f} km")
print()
print(f"SET B (setelah koreksi):")
print(f"  Tabrakan: {impacts_B}/{N_SIMULATIONS}")
print(f"  Probabilitas: {prob_B:.2f}%")
print(f"  Jarak minimum rata-rata: {np.mean(min_dists_B)/1000:.0f} km")
print(f"  Jarak minimum terkecil:  {np.min(min_dists_B)/1000:.0f} km")

# ============================================================
# VISUALISASI
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# ---- Histogram Distribusi Jarak Minimum ----
ax = axes[0]
bins = 50
ax.hist(min_dists_A/AU, bins=bins, alpha=0.6, label=f'Set A (σ={SIGMA_POS_A/AU:.2f} AU, σv={SIGMA_VEL_A:.0f} m/s)', color='orange')
ax.hist(min_dists_B/AU, bins=bins, alpha=0.6, label=f'Set B (σ={SIGMA_POS_B/AU:.3f} AU, σv={SIGMA_VEL_B:.0f} m/s)', color='blue')
ax.axvline(R_EARTH/AU, color='red', linestyle='--', linewidth=2, label=f'Radius Bumi ({R_EARTH/1000:.0f} km)')
ax.set_xlabel('Jarak Minimum ke Bumi (AU)')
ax.set_ylabel('Frekuensi')
ax.set_title(f'Distribusi Jarak Minimum ({N_SIMULATIONS} simulasi)')
ax.legend()
ax.grid(True, alpha=0.3)

# ---- Scatter Plot Beberapa Lintasan ----
ax = axes[1]
ax.scatter([0], [0], s=200, c='yellow', edgecolor='orange', zorder=5, label='Matahari')
earth_circle = Circle((AU, 0), R_EARTH/AU*50, color='blue', alpha=0.5, label='Bumi (diperbesar 50x)')
ax.add_patch(earth_circle)

# Plot 5 lintasan dari Set B
np.random.seed(42)
for i in range(5):
    dr = np.random.normal(0, SIGMA_POS_B, 3)
    dv = np.random.normal(0, SIGMA_VEL_B, 3)
    r0 = r_ast_nominal + dr
    v0 = v_ast_nominal + dv
    _, sol = run_single_sim(r0, v0)
    ax.plot(sol.y[6]/AU, sol.y[7]/AU, linewidth=0.8, alpha=0.7)

ax.set_xlabel('x [AU]'); ax.set_ylabel('y [AU]')
ax.set_title('Contoh Lintasan dari Set B (5 sampel)')
ax.axis('equal'); ax.legend(); ax.grid(True, alpha=0.3)
ax.set_xlim(-2, 2); ax.set_ylim(-2, 2)

plt.tight_layout()
plt.savefig('images/monte_carlo_results.png', dpi=150)
plt.show()

print("\nPlot tersimpan di images/monte_carlo_results.png")