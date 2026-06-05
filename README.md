# 🌍 Skjold-9: Simulasi Interaktif Ancaman Asteroid Antarbintang

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![HTML5 Canvas](https://img.shields.io/badge/HTML5-Canvas-orange)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-web--interactive-blue)

> *"Kiamat tidak berisik. Ia muncul sebagai koma yang salah tempat dalam spreadsheet, sebagai outlier yang diabaikan karena tidak cocok dengan model."*  
> — Leila Vance, Astrofisikawan, Proyek Vigil

---

## 📖 DAFTAR ISI
- [Konteks Cerita](#-konteks-cerita)
- [Fondasi Ilmiah](#-fondasi-ilmiah)
- [Arsitektur Baru Proyek](#-arsitektur-baru-proyek)
- [Fitur Utama Versi Web](#-fitur-utama-versi-web)
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

---

### 2. Percepatan Gravitasi
**Rumus:**
$$\vec{a} = -\frac{GM}{r^2} \hat{r}$$

**Mengapa digunakan:** Lebih praktis daripada menghitung gaya lalu membagi massa. Langsung digunakan untuk update kecepatan dalam integrator.

---

### 3. Superposisi Gaya Gravitasi (N-Body)
**Rumus:**
$$\vec{a}_i = \sum_{j \neq i} G m_j \frac{\vec{r}_j - \vec{r}_i}{|\vec{r}_j - \vec{r}_i|^3}$$

**Mengapa digunakan:** Tata surya bukan sistem dua benda. Bumi dan Matahari semuanya mempengaruhi asteroid. Superposisi memungkinkan simulasi realistis.

---

### 4. Kecepatan Orbit Lingkaran
**Rumus:**
$$v_{\text{circ}} = \sqrt{\frac{GM}{r}}$$

**Mengapa digunakan:** Menentukan kecepatan awal planet agar berada di orbit stabil, dan sebagai referensi apakah asteroid "terikat" atau "lepas".

---

### 5. Energi Mekanik Orbit (Specific Orbital Energy)
**Rumus:**
$$\epsilon = \frac{1}{2}v^2 - \frac{GM}{r}$$

**Mengapa digunakan:** Menentukan jenis orbit:
* $\epsilon < 0$ → terikat (elips/lingkaran)
* $\epsilon = 0$ → batas lepas (parabola)
* $\epsilon > 0$ → lintasan lepas (hiperbola)

Sangat sensitif terhadap kesalahan kecepatan, sehingga penting dalam analisis error.

---

### 6. Persamaan Vis-Viva
**Rumus:**
$$v = \sqrt{GM \left( \frac{2}{r} - \frac{1}{a} \right)}$$

---

### 7. Hukum Kepler III (Periode Orbit)
**Rumus:**
$$T = 2\pi \sqrt{\frac{a^3}{GM}}$$

**Mengapa digunakan:** Memvalidasi orbit planet dalam simulasi. Jika periode Bumi dalam simulasi ≈ 365.25 hari, sistem bekerja dengan benar.

---

### 8. Integrasi Numerik (Runge-Kutta Orde 4/5)
**Konsep:** Persamaan gerak N-benda tidak memiliki solusi analitik. Oleh karena itu, posisi dan kecepatan dihitung secara bertahap menggunakan metode **Runge-Kutta-Fehlberg (RK45)** yang adaptif—jauh lebih akurat daripada Euler.
`scipy.integrate.solve_ivp` dengan `method='RK45'` memberikan keseimbangan optimal antara kecepatan dan akurasi.

---

### 9. Simulasi Monte Carlo untuk Probabilitas Tabrakan
**Konsep:** Menjalankan ribuan simulasi dengan variasi acak kecil pada kondisi awal (posisi, kecepatan) untuk menghitung persentase skenario yang berujung tabrakan.

---

## 🏗️ ARSITEKTUR BARU PROYEK

Proyek ini telah dimigrasikan ke arsitektur web client-server untuk visualisasi interaktif yang lebih fleksibel dan berperforma tinggi.

```
skjold9_sim/
├── server.py                        # FastAPI web server & API endpoints
├── simulation_engine.py             # Engine komputasi & simulasi fisika (ODE & Monte Carlo)
├── utils.py                         # Konstanta fisika & utilitas rumus gravitasi
├── migration_guide.md               # Dokumentasi detail migrasi & cara instalasi
├── requirements.txt                 # Dependensi Python web
├── test_engine.py                   # Script testing dasar untuk engine
├── web/                             # Aset frontend statis
│   ├── index.html                   # Antarmuka web utama (glassmorphic UI)
│   ├── css/
│   │   └── style.css                # Desain tema gelap luar angkasa & animasi
│   └── js/
│       ├── api-client.js            # Penghubung REST API & SSE Monte Carlo
│       ├── orbit-renderer.js        # Engine rendering orbit Canvas 2D
│       └── app.js                   # Kontrol logika UI & update real-time
└── legacy/                          # Kode simulasi CLI / Dear PyGui lama
    ├── sim_1_basic_2body.py
    ├── sim_2_anomaly_hidden.py
    ├── sim_3_monte_carlo_impact_prob.py
    └── sim_3_optimized.py
```

---

## 🌟 FITUR UTAMA VERSI WEB

1. **Tuning Parameter Real-time**: Geser parameter posisi X/Y atau kecepatan X/Y asteroid, dan visualisasi orbit akan langsung ter-render ulang secara otomatis (dengan debounce 300ms agar server tetap responsif).
2. **Pendeteksi Anomali Gravitasi**: Bandingkan orbit prediksi (tanpa anomali) dan orbit nyata (dengan gaya non-gravitasi outgassing). Dilengkapi dengan grafik deviasi posisi logaritmik berbasis SVG dan deteksi hari kritis ketika deviasi melewati 10.000 km.
3. **Simulasi Monte Carlo dengan Progres Live**: Menjalankan simulasi acak paralel menggunakan multi-core CPU. Progress bar diupdate secara real-time melalui streaming **Server-Sent Events (SSE)**, lengkap dengan histogram interaktif dan rendering 5 lintasan terdekat.
4. **Sistem Desain Premium**: Visualisasi berbasis HTML5 Canvas dengan pendaran cahaya Matahari (radial glow), efek halo Bumi, gradien warna asteroid dinamis, serta interaksi zoom dan pan kamera yang mulus (*easing*).

---

## 🚀 RENCANA PENGEMBANGAN

### Fase 1 & 2: Fondasi & Web Interaktif (✅ Selesai)
* [x] Integrasi fisika 3-benda dasar (Runge-Kutta 45)
* [x] Simulasi deviasi anomali dan outgassing
* [x] Monte Carlo dengan multi-processing
* [x] Migrasi ke antarmuka web FastAPI + Canvas 2D
* [x] Fitur tuning real-time, grafik SVG deviasi, dan histogram HTML

### Fase 3: Visual 3D & Real-Time (📋 Rencana)
* [ ] Pilihan mode rendering 3D menggunakan Three.js/WebGL
* [ ] Animasi lintasan asteroid sepanjang waktu berjalan (*playback mode*)
* [ ] Visualisasi simulasi misi defleksi (kinetic impactor)

### Fase 4: Skjold-9 Story Mode (📋 Rencana Jangka Panjang)
* [ ] Game simulasi interaktif berbasis cerita (*visual novel/simulator*)
* [ ] Pengambilan keputusan kritis sebagai pemimpin Tim Vigil
* [ ] Integrasi data JPL Horizons untuk posisi planet tata surya yang nyata

---

## 🚦 CARA MENJALANKAN

### Prasyarat
* Python 3.9+
* Browser modern (Chrome, Edge, Firefox, Safari)

### Instalasi & Menjalankan Server
1. Clone repositori ke komputer lokal:
   ```bash
   git clone https://github.com/INTpras334/skjold9-simulator-engine.git
   cd skjold9_sim
   ```
2. Buat dan aktifkan virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate      # Windows CMD
   # atau jika menggunakan Windows PowerShell:
   # .\venv\Scripts\Activate.ps1
   ```
3. Instal semua dependensi:
   ```bash
   pip install -r requirements.txt
   ```
4. Jalankan server:
   ```bash
   python server.py
   ```

Setelah server aktif, buka browser Anda dan akses:
- **Aplikasi Visualizer**: [http://localhost:8000/](http://localhost:8000/)
- **Dokumentasi API (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📜 LISENSI

MIT License — bebas digunakan, dimodifikasi, dan didistribusikan.

---

**Dibuat oleh INTpras334** *Orang Gabut Buat cerita lalu divisualisasikan*
