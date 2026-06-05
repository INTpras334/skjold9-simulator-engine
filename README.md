# Skjold-9 Impact Simulation

Prototipe simulasi asteroid antarbintang yang nyaris menabrak Bumi. Proyek ini dibangun bertahap untuk memodelkan bagaimana anomali kecil dalam trajektori bisa terabaikan oleh model standar.

## Tahapan
1. `sim_1_basic_2body.py` — Simulasi 3-benda dasar (Matahari, Bumi, Asteroid)
2. `sim_2_anomaly_hidden.py` — Menambahkan gaya non-gravitasi kecil yang menghasilkan deviasi
3. `sim_3_monte_carlo_impact_prob.py` — Simulasi Monte Carlo untuk probabilitas tabrakan

## Menjalankan
```bash
pip install -r requirements.txt
python sim_1_basic_2body.py