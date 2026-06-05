# 🌍 Skjold-9: Simulasi Interaktif Ancaman Asteroid Antarbintang

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active--development-orange)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

> *"Kiamat tidak berisik. Ia muncul sebagai koma yang salah tempat dalam spreadsheet, sebagai outlier yang diabaikan karena tidak cocok dengan model."*  
> — Leila Vance, Astrofisikawan, Proyek Vigil

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
\[
\vec{F}_{12} = -G \frac{m_1 m_2}{r^2} \hat{r}
\]
**Mengapa digunakan:**  
Dasar dari semua interaksi dalam simulasi. Menentukan bagaimana Matahari, planet, dan asteroid saling mempengaruhi.

**Implementasi Python:**
```python
def gravitational_force(m1, m2, r_vec):
    r = np.linalg.norm(r_vec)
    return -G * m1 * m2 / r**2 * (r_vec / r)
