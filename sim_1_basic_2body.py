import os

# Copy-paste 2 baris ini di paling atas file sim_2_anomaly_hidden.py kamu
os.environ['TCL_LIBRARY'] = r'D:\laragon\bin\python\python-3.13\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'D:\laragon\bin\python\python-3.13\tcl\tk8.6'

# Sisa kode import bawaanmu ke bawah...
import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# Konstanta (SI)
G = 6.67430e-11
M_sun = 1.989e30
M_earth = 5.972e24
AU = 1.496e11
year = 365.25 * 24 * 3600

# Kondisi awal
# Bumi di sumbu x positif, kecepatan ke arah y
r_earth = np.array([AU, 0.0, 0.0])
v_earth = np.array([0.0, 2.978e4, 0.0])  # ~29.78 km/s

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
    a_e = -G * M_sun * r_e / np.linalg.norm(r_e)**3
    # Percepatan asteroid akibat Matahari + Bumi
    a_a_sun = -G * M_sun * r_a / np.linalg.norm(r_a)**3
    r_ae = r_a - r_e
    a_a_earth = -G * M_earth * r_ae / np.linalg.norm(r_ae)**3
    a_a = a_a_sun + a_a_earth
    
    return np.concatenate([v_e, a_e, v_a, a_a])

# Integrasi selama 3 tahun
t_span = (0, 3 * year)
sol = solve_ivp(deriv, t_span, y0, max_step=1e5, rtol=1e-9)

# Plot
plt.figure(figsize=(8,8))
plt.plot(sol.y[0]/AU, sol.y[1]/AU, label='Earth')
plt.plot(sol.y[6]/AU, sol.y[7]/AU, label='Asteroid')
plt.scatter([0], [0], s=200, c='yellow', label='Sun')
plt.legend()
plt.axis('equal')
plt.xlabel('x [AU]')
plt.ylabel('y [AU]')
plt.title('Basic 3-Body Simulation')
plt.grid(True)
plt.show()