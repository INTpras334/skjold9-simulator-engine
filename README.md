# 🌍 Skjold-9: Simulasi Asteroid Antarbintang & Anomali Trajektori

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-prototype-orange)

Proyek ini adalah prototipe simulasi numerik tiga benda (Matahari, Bumi, Asteroid) yang terinspirasi dari cerita fiksi ilmiah **Skjold-9** — sebuah objek antarbintang raksasa yang nyaris memusnahkan peradaban manusia karena kesalahan klasifikasi dan anomali kecil yang terabaikan.

Simulasi dibangun secara bertahap untuk menunjukkan bagaimana **deviasi kecil dalam trajektori asteroid**, jika tidak terdeteksi, dapat mengubah probabilitas tabrakan dari nyaris nol menjadi nyaris pasti — persis seperti yang terjadi dalam narasi Skjold-9.

---

## 📖 Latar Belakang Cerita

Pada tahun 2005, sebuah objek antarbintang bernama **Skjold-9** terdeteksi oleh jaringan observasi internasional. Karena keterbatasan data dan kepercayaan berlebihan pada model standar, objek ini diklasifikasikan sebagai *low threat* dan diabaikan.

Beberapa bulan kemudian, seorang intern (Leila Vance) dan engineer fasilitas (Matias Okonkwo) menemukan **ketidaksesuaian kecil namun konsisten** dalam lintasannya. Setelah analisis ulang, terungkap bahwa serangkaian asumsi yang salah (albedo, massa, rekonstruksi posisi) telah menyembunyikan kenyataan bahwa Skjold-9 sebenarnya berada di jalur tabrakan langsung dengan Bumi.

**Probabilitas tabrakan direvisi dari 0% menjadi 99,999%.**  
Manusia hanya punya waktu 4 tahun untuk menyelamatkan diri.

> Simulasi ini bertujuan untuk memodelkan *bagaimana* anomali sekecil itu bisa tersembunyi dalam data, dan mengapa model standar gagal mendeteksinya.

---

## 🧪 Tujuan Proyek

1. Membangun simulasi gravitasi N-benda menggunakan Python dan integrasi numerik.
2. Menunjukkan pengaruh **gaya non-gravitasi kecil** (contoh: outgassing termal) terhadap lintasan asteroid.
3. Membandingkan lintasan **prediksi** (model standar) vs **aktual** (dengan anomali).
4. Menghitung **probabilitas tabrakan** melalui simulasi Monte Carlo.
5. Menyediakan alat pembelajaran interaktif untuk memahami dinamika orbital dan analisis risiko.

---

## 🚀 Tahapan Pengembangan

Proyek dibagi menjadi tiga file utama sesuai tingkat kompleksitas:

| File | Deskripsi | Status |
|------|-----------|--------|
| `sim_1_basic_2body.py` | Simulasi 3-benda dasar (Matahari, Bumi, Asteroid) dengan gravitasi Newton murni. | ✅ Selesai |
| `sim_2_anomaly_hidden.py` | Menambahkan gaya non-gravitasi kecil (outgassing) dan membandingkan lintasan prediksi vs aktual. | ⏳ Dalam pengembangan |
| `sim_3_monte_carlo_impact_prob.py` | Simulasi Monte Carlo untuk menghitung probabilitas tabrakan dengan variasi parameter awal. | ❌ Rencana |

---

## 🛠️ Teknologi yang Digunakan

- **Python 3.9+** — Bahasa pemrograman utama.
- **NumPy** — Komputasi numerik dan operasi vektor.
- **SciPy** — Integrator persamaan diferensial (`solve_ivp`).
- **Matplotlib** — Visualisasi orbit 2D dan 3D.
- **Astropy** — Konstanta dan satuan astronomi.
- **Poliastro** (opsional) — Astrodinamika dan propagasi orbit.
- **JupyterLab** — Notebook interaktif (jika digunakan).

---

## 📦 Instalasi

### 1. Clone repositori
```bash
git clone https://github.com/USERNAME/skjold9_sim.git
cd skjold9_sim
