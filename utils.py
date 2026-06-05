"""
utils.py
Modul fisika untuk simulasi N-benda Tata Surya.
Berisi semua rumus dasar gravitasi dan dinamika orbital.
"""

import numpy as np

# ============================================================
# KONSTANTA FISIKA
# ============================================================
G = 6.67430e-11                # Konstanta gravitasi universal (m^3 kg^-1 s^-2)

# Massa benda langit (kg)
M_SUN = 1.989e30
M_EARTH = 5.972e24
M_VENUS = 4.867e24
M_MARS = 6.417e23
M_JUPITER = 1.898e27

# Jarak (m)
AU = 1.496e11                  # 1 Astronomical Unit

# Waktu (s)
YEAR = 365.25 * 24 * 3600
DAY = 24 * 3600


# ============================================================
# 1. GAYA GRAVITASI NEWTON (VEKTOR PENUH)
# ============================================================
def gravitational_force(m1, m2, r_vec):
    """
    Menghitung gaya gravitasi antara dua massa.
    
    Parameters:
        m1, m2 : float : Massa benda 1 dan 2 (kg)
        r_vec  : np.array(3) : Vektor posisi dari m1 ke m2 (m)
    
    Returns:
        np.array(3) : Gaya gravitasi pada m2 akibat m1 (Newton)
    """
    r = np.linalg.norm(r_vec)
    if r == 0:
        return np.zeros(3)
    return -G * m1 * m2 / r**2 * (r_vec / r)


# ============================================================
# 2. PERCEPATAN GRAVITASI (OLEH SATU MASSA)
# ============================================================
def gravitational_acceleration(M, r_vec):
    """
    Menghitung percepatan gravitasi akibat massa M.
    
    Parameters:
        M     : float : Massa sumber gravitasi (kg)
        r_vec : np.array(3) : Vektor dari sumber ke objek (m)
    
    Returns:
        np.array(3) : Vektor percepatan gravitasi (m/s^2)
    """
    r = np.linalg.norm(r_vec)
    if r == 0:
        return np.zeros(3)
    return -G * M * r_vec / r**3


# ============================================================
# 3. SUPERPOSISI PERCEPATAN N-BENDA
# ============================================================
def total_acceleration(pos, bodies):
    """
    Menghitung percepatan total dari semua benda bermassa.
    
    Parameters:
        pos    : np.array(3) : Posisi objek yang ditinjau (m)
        bodies : list of dict : Setiap dict punya kunci 'mass' (float) 
                                dan 'pos' (np.array(3))
    
    Returns:
        np.array(3) : Percepatan total (m/s^2)
    """
    a = np.zeros(3)
    for body in bodies:
        r_vec = body["pos"] - pos
        r = np.linalg.norm(r_vec)
        if r == 0:
            continue
        a += G * body["mass"] * r_vec / r**3
    return a


# ============================================================
# 4. KECEPATAN ORBIT LINGKARAN
# ============================================================
def orbital_velocity(M, r):
    """
    Kecepatan untuk orbit lingkaran di sekitar massa M.
    
    Parameters:
        M : float : Massa pusat (kg)
        r : float : Jarak dari pusat (m)
    
    Returns:
        float : Kecepatan orbit lingkaran (m/s)
    """
    return np.sqrt(G * M / r)


# ============================================================
# 5. ENERGI MEKANIK SPESIFIK
# ============================================================
def specific_energy(v_vec, r, M):
    """
    Energi mekanik per satuan massa (epsilon).
    
    Parameters:
        v_vec : np.array(3) : Vektor kecepatan (m/s)
        r     : float       : Jarak dari pusat massa (m)
        M     : float       : Massa pusat (kg)
    
    Returns:
        float : epsilon (J/kg)
               negatif -> orbit terikat (elips/lingkaran)
               nol     -> batas lepas (parabola)
               positif -> lintasan lepas (hiperbola)
    """
    v = np.linalg.norm(v_vec)
    return 0.5 * v**2 - G * M / r


# ============================================================
# 6. PERSAMAAN VIS-VIVA
# ============================================================
def vis_viva_velocity(M, r, a):
    """
    Kecepatan berdasarkan persamaan Vis-Viva.
    
    Parameters:
        M : float : Massa pusat (kg)
        r : float : Jarak saat ini dari pusat (m)
        a : float : Semi-major axis orbit (m)
                    Untuk hiperbola, a negatif.
    
    Returns:
        float : Kecepatan pada jarak r (m/s)
    """
    return np.sqrt(G * M * (2.0 / r - 1.0 / a))


# ============================================================
# 7. PERIODE ORBIT (HUKUM KEPLER III)
# ============================================================
def orbital_period(M, a):
    """
    Periode orbit berdasarkan Hukum Kepler III.
    
    Parameters:
        M : float : Massa pusat (kg)
        a : float : Semi-major axis (m)
    
    Returns:
        float : Periode orbit (detik)
    """
    return 2.0 * np.pi * np.sqrt(a**3 / (G * M))


# ============================================================
# 8. INTEGRASI EULER (UNTUK DEMO / PROTOTIPE CEPAT)
# ============================================================
def update_euler(pos, vel, acc, dt):
    """
    Satu langkah integrasi Euler.
    CATATAN: Untuk simulasi akurat jangka panjang, gunakan RK45 dari SciPy.
    
    Parameters:
        pos : np.array(3) : Posisi saat ini (m)
        vel : np.array(3) : Kecepatan saat ini (m/s)
        acc : np.array(3) : Percepatan saat ini (m/s^2)
        dt  : float       : Langkah waktu (s)
    
    Returns:
        tuple (np.array(3), np.array(3)) : (posisi baru, kecepatan baru)
    """
    vel_new = vel + acc * dt
    pos_new = pos + vel * dt
    return pos_new, vel_new


# ============================================================
# 9. PARAMETER GRAVITASI STANDAR (MU)
# ============================================================
def mu(M):
    """
    Parameter gravitasi standar (mu = G * M).
    
    Parameters:
        M : float : Massa benda (kg)
    
    Returns:
        float : mu (m^3/s^2)
    """
    return G * M


# ============================================================
# FUNGSI TAMBAHAN YANG BERGUNA
# ============================================================

def distance(p1, p2):
    """Jarak Euclidean antara dua titik."""
    return np.linalg.norm(np.array(p1) - np.array(p2))


def unit_vector(v):
    """Vektor satuan dari vektor input."""
    norm = np.linalg.norm(v)
    if norm == 0:
        return np.zeros_like(v)
    return v / norm


def impact_parameter(v_inf, M, r_min):
    """
    Menghitung parameter impak dari kecepatan datang dan jarak terdekat.
    Berguna untuk analisis apakah asteroid akan menabrak planet.
    
    Parameters:
        v_inf : float : Kecepatan relatif di tak hingga (m/s)
        M     : float : Massa planet (kg)
        r_min : float : Jarak terdekat yang diinginkan (m) [misal: radius planet]
    
    Returns:
        float : b (parameter impak) dalam meter
    """
    return r_min * np.sqrt(1 + (2 * G * M) / (r_min * v_inf**2))