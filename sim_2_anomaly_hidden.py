"""
sim_2_anomaly_hidden.py
Simulasi anomali tersembunyi menggunakan modul utils.py.
"""

import os
import sys
os.environ['TCL_LIBRARY'] = r'D:\laragon\bin\python\python-3.13\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'D:\laragon\bin\python\python-3.13\tcl\tk8.6'

import matplotlib
matplotlib.use('Agg')  # Gunakan 'TkAgg' jika Tcl/Tk sudah diperbaiki

import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# Modul fisika kita
from utils import (
    G, M_SUN, M_EARTH, AU, YEAR, DAY,
    gravitational_acceleration, total_acceleration,
    orbital_velocity, specific_energy
)

# ============================================================
# ANOMALI TERSEMBUNYI
# ============================================================
ANOMALI_ACCEL = np.array([1e-6, 3e-8, -2e-8])  # m/s^2

# ============================================================
# KONDISI AWAL
# ============================================================
r_earth = np.array([AU, 0.0, 0.0])
v_earth = np.array([0.0, orbital_velocity(M_SUN, AU), 0.0])

r_ast0 = np.array([-1.2 * AU, 0.5 * AU, 0.0])
v_ast0 = np.array([1.8e4, -4.5e3, 0.0])

y0 = np.concatenate([r_earth, v_earth, r_ast0, v_ast0])

# ============================================================
# FUNGSI TURUNAN
# ============================================================
def make_deriv(include_anomaly=False):
    def deriv(t, y):
        r_e = y[0:3]; v_e = y[3:6]
        r_a = y[6:9]; v_a = y[9:12]

        # Bumi hanya dipengaruhi Matahari
        a_e = gravitational_acceleration(M_SUN, r_e)

        # Asteroid dipengaruhi Matahari + Bumi
        a_a = gravitational_acceleration(M_SUN, r_a) + \
              gravitational_acceleration(M_EARTH, r_a - r_e)

        if include_anomaly:
            a_a = a_a + ANOMALI_ACCEL

        return np.concatenate([v_e, a_e, v_a, a_a])
    return deriv

# ============================================================
# INTEGRASI
# ============================================================
t_span = (0, 3 * YEAR)
t_eval = np.linspace(0, 3 * YEAR, 2000)

print("Simulasi prediksi...")
sol_pred = solve_ivp(make_deriv(False), t_span, y0, t_eval=t_eval,
                     max_step=DAY, rtol=1e-9)

print("Simulasi aktual (dengan anomali)...")
sol_actual = solve_ivp(make_deriv(True), t_span, y0, t_eval=t_eval,
                       max_step=DAY, rtol=1e-9)

# ============================================================
# ANALISIS
# ============================================================
r_pred = sol_pred.y[6:9, :]
r_actual = sol_actual.y[6:9, :]
diff = np.linalg.norm(r_actual - r_pred, axis=0)

significant_idx = np.argmax(diff > 1e7) if np.any(diff > 1e7) else -1
if significant_idx > 0:
    t_sig = sol_pred.t[significant_idx] / DAY
    print(f"Deviasi > 10.000 km setelah {t_sig:.1f} hari")
else:
    print("Deviasi tidak mencapai 10.000 km dalam 3 tahun")

# ============================================================
# PLOT
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

ax = axes[0]
ax.plot(sol_pred.y[0]/AU, sol_pred.y[1]/AU, 'b-', alpha=0.3, label='Earth')
ax.plot(r_pred[0]/AU, r_pred[1]/AU, 'g--', label='Predicted')
ax.plot(r_actual[0]/AU, r_actual[1]/AU, 'r-', label='Actual')
ax.scatter([0], [0], s=200, c='yellow', label='Sun')
ax.set_xlabel('x [AU]'); ax.set_ylabel('y [AU]')
ax.set_title('Lintasan Asteroid: Prediksi vs Aktual')
ax.legend(); ax.axis('equal'); ax.grid(True)

ax = axes[1]
dist_to_earth = np.linalg.norm(r_actual - sol_actual.y[0:3, :], axis=0)
close = dist_to_earth < 0.2 * AU
if np.any(close):
    ax.plot(sol_pred.y[0, close]/AU, sol_pred.y[1, close]/AU, 'b-', label='Earth')
    ax.plot(r_pred[0, close]/AU, r_pred[1, close]/AU, 'g--', label='Predicted')
    ax.plot(r_actual[0, close]/AU, r_actual[1, close]/AU, 'r-', label='Actual')
    ax.set_xlabel('x [AU]'); ax.set_ylabel('y [AU]')
    ax.set_title('Zoom di Dekat Bumi')
    ax.legend(); ax.axis('equal'); ax.grid(True)
else:
    ax.text(0.5, 0.5, 'Tidak ada pendekatan dekat', ha='center', transform=ax.transAxes)

ax = axes[2]
t_days = sol_pred.t / DAY
ax.semilogy(t_days, diff/1000, 'k-')
ax.axhline(1e4, color='red', linestyle='--', label='10.000 km')
ax.set_xlabel('Waktu (hari)'); ax.set_ylabel('Deviasi (km)')
ax.set_title('Akumulasi Deviasi Akibat Anomali')
ax.legend(); ax.grid(True)

plt.tight_layout()
plt.savefig('images/anomaly_comparison.png', dpi=150)
print("Plot tersimpan di images/anomaly_comparison.png")