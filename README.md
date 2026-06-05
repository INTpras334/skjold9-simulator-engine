$readmeContent = @'
# 🌍 Skjold-9: Simulasi Interaktif Ancaman Asteroid Antarbintang

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active--development-orange)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

> *"Kiamat tidak berisik. Ia muncul sebagai koma yang salah tempat dalam spreadsheet, sebagai outlier yang diabaikan karena tidak cocok dengan model."* > — Leila Vance, Astrofisikawan, Proyek Vigil

---

## 📖 DAFTAR ISI
- [Konteks Cerita](#-konteks-cerita)
- [Fondasi Ilmiah](#-fondasi-ilmiah)
- [Arsitektur Proyek](#-arsitektur-proyek)
- [Rencana Pengembangan](#-rencana-pengembangan)
- [Potensi Portofolio](#-potensi-portofolio)
- [Cara Menjalankan](#-cara-menjalankan)
- [Kontribusi](#-kontribusi)
- [Lisensi](#-lisensi)

---

## 📚 KONTEKS CERITA

### Premis Utama
Pada tahun 2005, sebuah objek antarbintang bernama **Skjold-9** terdeteksi oleh jaringan observasi internasional. Ukurannya yang luar biasa besar—cukup untuk diklasifikasikan sebagai *planet-killer*—seharusnya menjadikannya prioritas utama. Namun karena serangkaian asumsi yang salah (albedo, massa, rekonstruksi posisi 3D) dan kepercayaan berlebihan pada model standar, objek ini diklasifikasikan sebagai *low threat object* dan diabaikan.

Beberapa bulan kemudian, seorang intern bernama **Leila Vance** bersama engineer **Matias Okonkwo** menemukan ketidaksesuaian kecil namun konsisten dalam data lintasan. Setelah analisis ulang, terungkap bahwa **Skjold-9 sebenarnya berada pada jalur tabrakan langsung dengan Bumi**. Probabilitas yang semula nyaris 0% direvisi menjadi **99,999%**, dengan waktu tumbukan diproyeksikan pada **23 September 2010**—hanya 4 tahun lagi.

Kisah ini bukan tentang asteroid yang tiba-tiba muncul, melainkan tentang **kegagalan epistemik**: bagaimana rantai asumsi yang saling memperkuat dapat menyembunyikan ancaman eksistensial.

### Timeline Singkat
| Tahun | Kejadian |
|-------|----------|
| 2005 | Skjold-9 terdeteksi, diklasifikasikan *low threat* |
| 2006 (awal) | Leila & Matias menemukan anomali kecil |
| Sep 2006 | Probabilitas tabrakan direvisi menjadi 99,999% |
| 2006–2010 | Proyek Vigil: misi defleksi global |
| Jul 2009 | Gelombang pertama impactor hanya mencapai 72% target |
| Okt 2009 | Gelombang kedua + defleksi nuklir berhasil |
| 23 Sep 2010 | Skjold-9 melintas pada jarak 43.000 km, Bumi selamat |
| 2011–2017 | Investigasi forensik: Skjold-9 adalah artefak peradaban mati |
| Mar 2017 | Sinyal gamma misterius dari Skjold-9 terdeteksi |
| 2017–2020 | Proyek ECHO: pelacakan asal-usul dan sinyal lanjutan |

---

## 🔬 FONDASI ILMIAH

Semua simulasi dalam proyek ini dibangun di atas hukum fisika yang valid. Berikut adalah rumus dan konsep yang digunakan, beserta justifikasi penggunaannya.

### 1. Hukum Gravitasi Newton
**Rumus:**
$$\vec{F}_{12} = -G \frac{m_1 m_2}{r^2} \hat{r}$$

**Mengapa digunakan:** Dasar dari semua interaksi dalam simulasi. Menentukan bagaimana Matahari, planet, dan asteroid saling mempengaruhi.

**Implementasi Python:**
```python
def gravitational_force(m1, m2, r_vec):
    r = np.linalg.norm(r_vec)
    return -G * m1 * m2 / r**2 * (r_vec / r)

```

---

### 2. Percepatan Gravitasi

**Rumus:**


$$\vec{a} = -\frac{GM}{r^2} \hat{r}$$

**Mengapa digunakan:** Lebih praktis daripada menghitung gaya lalu membagi massa. Langsung digunakan untuk update kecepatan dalam integrator.

**Implementasi Python:**

```python
def gravitational_acceleration(M, r_vec):
    r = np.linalg.norm(r_vec)
    return -G * M * r_vec / r**3

```

---

### 3. Superposisi Gaya Gravitasi (N-Body)

**Rumus:**


$$\vec{a}_i = \sum_{j \neq i} G m_j \frac{\vec{r}_j - \vec{r}_i}{|\vec{r}_j - \vec{r}_i|^3}$$

**Mengapa digunakan:** Tata surya bukan sistem dua benda. Venus, Bumi, dan Matahari semuanya mempengaruhi asteroid. Superposisi memungkinkan simulasi realistis.

**Implementasi Python:**

```python
def total_acceleration(pos, bodies):
    a = np.zeros(3)
    for body in bodies:
        r_vec = body["pos"] - pos
        r = np.linalg.norm(r_vec)
        a += G * body["mass"] * r_vec / r**3
    return a

```

---

### 4. Kecepatan Orbit Lingkaran

**Rumus:**


$$v_{\text{circ}} = \sqrt{\frac{GM}{r}}$$

**Mengapa digunakan:** Menentukan kecepatan awal planet agar berada di orbit stabil, dan sebagai referensi apakah asteroid "terikat" atau "lepas".

**Implementasi Python:**

```python
def orbital_velocity(M, r):
    return np.sqrt(G * M / r)

```

---

### 5. Energi Mekanik Orbit (Specific Orbital Energy)

**Rumus:**


$$\epsilon = \frac{1}{2}v^2 - \frac{GM}{r}$$

**Mengapa digunakan:** Menentukan jenis orbit:

* $\epsilon < 0$ → terikat (elips/lingkaran)
* $\epsilon = 0$ → batas lepas (parabola)
* $\epsilon > 0$ → lintasan lepas (hiperbola)

Sangat sensitif terhadap kesalahan kecepatan, sehingga penting dalam analisis error.

**Implementasi Python:**

```python
def specific_energy(v_vec, r, M):
    v = np.linalg.norm(v_vec)
    return 0.5 * v**2 - G * M / r

```

---

### 6. Persamaan Vis-Viva

**Rumus:**


$$v = \sqrt{GM \left( \frac{2}{r} - \frac{1}{a} \right)}$$

**Mengapa digunakan:** Menghitung kecepatan asteroid di titik manapun dalam orbitnya. Berguna untuk validasi hasil simulasi.

**Implementasi Python:**

```python
def vis_viva_velocity(M, r, a):
    return np.sqrt(G * M * (2.0/r - 1.0/a))

```

---

### 7. Hukum Kepler III (Periode Orbit)

**Rumus:**


$$T = 2\pi \sqrt{\frac{a^3}{GM}}$$

**Mengapa digunakan:** Memvalidasi orbit planet dalam simulasi. Jika periode Bumi dalam simulasi ≈ 365.25 hari, sistem bekerja dengan benar.

**Implementasi Python:**

```python
def orbital_period(M, a):
    return 2 * np.pi * np.sqrt(a**3 / (G * M))

```

---

### 8. Integrasi Numerik (Runge-Kutta Orde 4/5)

**Konsep:** Persamaan gerak N-benda tidak memiliki solusi analitik. Oleh karena itu, posisi dan kecepatan dihitung secara bertahap menggunakan metode **Runge-Kutta-Fehlberg (RK45)** yang adaptif—jauh lebih akurat daripada Euler.

**Mengapa digunakan:** Menjadi inti komputasi seluruh simulasi. `scipy.integrate.solve_ivp` dengan `method='RK45'` memberikan keseimbangan optimal antara kecepatan dan akurasi.

**Implementasi Python:**

```python
from scipy.integrate import solve_ivp
sol = solve_ivp(deriv, t_span, y0, method='RK45', max_step=DAY, rtol=1e-9)

```

---

### 9. Parameter Gravitasi Standar (μ)

**Rumus:**


$$\mu = GM$$

**Mengapa digunakan:** Mempermudah perhitungan dan banyak digunakan dalam astrodinamika modern.

**Implementasi Python:**

```python
def mu(M):
    return G * M

```

---

### 10. Simulasi Monte Carlo untuk Probabilitas Tabrakan

**Konsep:** Menjalankan ribuan simulasi dengan variasi acak kecil pada kondisi awal (posisi, kecepatan) untuk menghitung persentase skenario yang berujung tabrakan.

**Mengapa digunakan:** Merefleksikan ketidakpastian data observasi nyata. Dalam cerita Skjold-9, inilah yang menyebabkan probabilitas direvisi dari 0% menjadi 99,999%.

**Implementasi Python:**

```python
def monte_carlo_parallel(sigma_pos, sigma_vel, n_sim):
    # Variasi acak pada r_ast0 dan v_ast0
    # Jalankan paralel dengan ProcessPoolExecutor
    # Hitung jumlah tabrakan / total simulasi
    return probabilitas

```

---

### Konsep Fundamental Tambahan

* **Sistem N-Body:** Semua benda saling mempengaruhi. Tidak ada orbit yang benar-benar statis.
* **Sensitivitas Kondisi Awal:** Kesalahan kecil dalam data observasi → perbedaan besar dalam lintasan jangka panjang. Inilah inti cerita.
* **Observasi ≠ Realitas:** Yang diamati adalah posisi & cahaya; yang dihitung adalah jarak, kecepatan, orbit. Semua model adalah hasil interpretasi, bukan kebenaran absolut.

---

## 🏗️ ARSITEKTUR PROYEK

### Struktur Folder Saat Ini

```
skjold9_sim/
├── README.md                        # Dokumen ini
├── requirements.txt                 # Dependensi Python
├── utils.py                         # Modul fisika (9 rumus + fungsi pendukung)
├── sim_1_basic_2body.py             # Tahap 1: Simulasi 3-benda dasar
├── sim_2_anomaly_hidden.py          # Tahap 2: Anomali tersembunyi & deviasi
├── sim_3_monte_carlo_impact_prob.py # Tahap 3: Monte Carlo probabilitas tabrakan
├── sim_3_optimized.py               # Tahap 3+: Ultra-cepat (early stopping + multiprocessing)
└── images/                          # Output visualisasi

```

### Teknologi yang Digunakan

| Library | Kegunaan |
| --- | --- |
| NumPy | Operasi vektor & matriks |
| SciPy | Integrator ODE (RK45) |
| Matplotlib | Visualisasi 2D/3D |
| Astropy | Konstanta & satuan astronomi |
| concurrent.futures | Multi-processing untuk Monte Carlo |

---

## 🚀 RENCANA PENGEMBANGAN

### Fase 1: Fondasi (✅ Selesai)

* [x] Simulasi gravitasi 3-benda dasar
* [x] Implementasi anomali tersembunyi
* [x] Monte Carlo probabilitas tabrakan
* [x] Optimasi early stopping & multi-processing

### Fase 2: Simulasi Interaktif (🔄 Dalam Pengembangan)

* [ ] **UI Desktop** dengan slider, tombol, dan plot real-time (target: Dear PyGui / PyQt)
* [ ] **Mode Skenario** mengikuti kronologi cerita Skjold-9
* [ ] **Mode Bebas** untuk eksperimen parameter
* [ ] **Probabilitas Live** yang ter-update saat slider digeser

### Fase 3: Visual 3D & Real-Time (📋 Rencana)

* [ ] Plot orbit 3D interaktif dengan kamera rotasi
* [ ] Animasi lintasan asteroid sepanjang waktu
* [ ] Visualisasi misi defleksi (kinetic impactor)
* [ ] Dukungan VR/Web (opsional, dengan Three.js)

### Fase 4: Skjold-9 Story Mode (📋 Rencana Jangka Panjang)

* [ ] Game simulasi interaktif berbasis cerita
* [ ] Pemain berperan sebagai tim Vigil yang harus mengambil keputusan kritis
* [ ] Multiple endings berdasarkan probabilitas tabrakan akhir
* [ ] Integrasi data JPL Horizons untuk posisi planet real-time

---

## 💼 POTENSI PORTOFOLIO

Proyek ini menunjukkan kemampuan di bidang-bidang berikut:

| Skill | Bukti |
| --- | --- |
| **Python tingkat lanjut** | Kode modular, OOP, dekorator, multi-processing |
| **Fisika komputasi** | Integrasi numerik ODE, N-body problem, Monte Carlo |
| **Visualisasi data** | Plot statis, animasi, plot 3D dengan Matplotlib |
| **Optimasi performa** | Early stopping, multi-processing, vectorization |
| **Desain UI/UX** | Antarmuka interaktif dengan slider real-time (mendatang) |
| **Dokumentasi teknis** | README terstruktur, docstring, diagram arsitektur |
| **Manajemen proyek** | Git, virtual environment, requirements.txt |

**Target audiens portofolio:**

* Perusahaan teknologi (software engineer, data scientist)
* Lembaga riset astronomi/astrofisika
* Studio game (simulasi fisika real-time)
* Program pascasarjana (komputasi sains)

---

## ▶️ CARA MENJALANKAN

### Prasyarat

* Python 3.9+
* Git

### Instalasi

```bash
git clone [https://github.com/INTpras334/skjold9-simulator-engine.git](https://github.com/INTpras334/skjold9-simulator-engine.git)
cd skjold9_sim
python -m venv venv
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows
pip install -r requirements.txt

```

### Menjalankan Simulasi

```bash
# Tahap 1: Simulasi dasar
python sim_1_basic_2body.py

# Tahap 2: Anomali tersembunyi
python sim_2_anomaly_hidden.py

# Tahap 3: Monte Carlo probabilitas
python sim_3_monte_carlo_impact_prob.py

# Tahap 3+: Monte Carlo ultra-cepat
python sim_3_optimized.py

```

---

## 🤝 KONTRIBUSI

Proyek ini terbuka untuk kontribusi. Beberapa ide:

* Menambahkan efek relativistik (post-Newtonian)
* Porting ke C++/Rust untuk performa maksimal
* Membangun mode multiplayer (tim Vigil kolaboratif)
* Menambahkan dataset asteroid nyata dari JPL

---

## 📜 LISENSI

MIT License — bebas digunakan, dimodifikasi, dan didistribusikan.

---

**Dibuat oleh INTpras334** *Orang Gabut Buat cerita lalu divisualisasikan*
'@

Set-Content -Path "README.md" -Value $readmeContent
