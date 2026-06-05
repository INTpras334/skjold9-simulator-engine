"""
sim_1_basic_2body.py
Simulasi 3-benda dasar: Matahari + Bumi + Asteroid.
Menggunakan modul utils.py untuk konstanta dan fungsi fisika.
"""

import numpy as np
from scipy.integrate import solve_ivp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Import dari modul fisika kita
from utils import (
    G, M_SUN, M_EARTH, AU, YEAR, DAY,
    gravitational_acceleration, orbital_velocity
)

# Kondisi awal
# Bumi di sumbu x positif, kecepatan ke arah y
r_earth = np.array([AU, 0.0, 0.0])
v_earth = np.array([0.0, orbital_velocity(M_SUN, AU), 0.0])

# Asteroid (posisi dan kecepatan awal diatur agar memiliki orbit yang berbeda)
r_ast = np.array([-1.2 * AU, 0.5 * AU, 0.0])
v_ast = np.array([1.8e4, -4.5e3, 0.0])

# Gabungkan state vektor: [rx_e, ry_e, rz_e, vx_e, vy_e, vz_e, rx_a, ry_a, rz_a, vx_a, vy_a, vz_a]
y0 = np.concatenate([r_earth, v_earth, r_ast, v_ast])

def deriv(t, y):
    # Unpack
    r_e = y[0:3]
    v_e = y[3:6]
    r_a = y[6:9]
    v_a = y[9:12]
    
    # Percepatan Bumi akibat Matahari
    a_e = gravitational_acceleration(M_SUN, r_e)
    # Percepatan asteroid akibat Matahari + Bumi
    a_a_sun = gravitational_acceleration(M_SUN, r_a)
    a_a_earth = gravitational_acceleration(M_EARTH, r_a - r_e)
    a_a = a_a_sun + a_a_earth
    
    return np.concatenate([v_e, a_e, v_a, a_a])

# Integrasi selama 3 tahun
t_span = (0, 3 * YEAR)
sol = solve_ivp(deriv, t_span, y0, max_step=DAY, rtol=1e-9)

# Plot
plt.figure(figsize=(8, 8))
plt.plot(sol.y[0]/AU, sol.y[1]/AU, label='Earth')
plt.plot(sol.y[6]/AU, sol.y[7]/AU, label='Asteroid')
plt.scatter([0], [0], s=200, c='yellow', label='Sun')
plt.legend()
plt.axis('equal')
plt.xlabel('x [AU]')
plt.ylabel('y [AU]')
plt.title('Basic 3-Body Simulation')
plt.grid(True)
plt.savefig('images/basic_3body.png', dpi=150)
print("Plot tersimpan di images/basic_3body.png")