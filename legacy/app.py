"""
app.py
Aplikasi Simulasi Interaktif Skjold-9
Fase 2: UI dengan Dear PyGui
"""

import os
import sys
# Path Tcl/Tk hanya jika kamu pakai Matplotlib backend TkAgg (opsional)
# os.environ['TCL_LIBRARY'] = r'D:\laragon\bin\python\python-3.13\tcl\tcl8.6'
# os.environ['TK_LIBRARY'] = r'D:\laragon\bin\python\python-3.13\tcl\tk8.6'

import dearpygui.dearpygui as dpg
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

# Import backend engine (kita akan buat terpisah atau inline dulu)
from utils import AU, M_SUN, M_EARTH, orbital_velocity

# ============================================================
# KONFIGURASI AWAL
# ============================================================
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800

# Parameter default (sama seperti di sim_3)
DEFAULT_R_X = -1.2   # AU
DEFAULT_R_Y = 0.5    # AU
DEFAULT_V_X = 18.0   # km/s
DEFAULT_V_Y = -4.5   # km/s
DEFAULT_ANOMALY = False
DEFAULT_ANOMALY_STRENGTH = 1.0  # faktor pengali 1e-7 m/s^2
DEFAULT_QUICK_N = 50
DEFAULT_FULL_N = 500

# ============================================================
# STATE GLOBAL (akan dipindahkan ke class nanti)
# ============================================================
current_params = {
    "r_x": DEFAULT_R_X,
    "r_y": DEFAULT_R_Y,
    "v_x": DEFAULT_V_X,
    "v_y": DEFAULT_V_Y,
    "anomaly_enabled": DEFAULT_ANOMALY,
    "anomaly_strength": DEFAULT_ANOMALY_STRENGTH,
    "quick_n": DEFAULT_QUICK_N,
    "full_n": DEFAULT_FULL_N,
    "probability": 0.0,
    "status": "Siap",
}

# ============================================================
# FUNGSI SIMULASI RINGAN (PLACEHOLDER)
# ============================================================
def run_quick_simulation():
    """Quick estimate: dipanggil saat slider berubah."""
    # Placeholder: nanti akan panggil backend sungguhan
    dpg.set_value("status_text", "Menghitung quick estimate...")
    dpg.set_value("prob_text", f"Probabilitas: --%")
    # Simulasi dummy: prob acak
    import random
    prob = random.uniform(0, 100)
    dpg.set_value("prob_text", f"Probabilitas: {prob:.1f}%")
    dpg.set_value("status_text", "Siap (quick estimate selesai)")

def run_full_monte_carlo():
    """Full Monte Carlo: dipanggil saat tombol ditekan."""
    dpg.set_value("status_text", "Menjalankan Monte Carlo penuh...")
    dpg.set_value("prob_text", f"Probabilitas: --%")
    # Placeholder
    import random
    prob = random.uniform(0, 100)
    dpg.set_value("prob_text", f"Probabilitas: {prob:.1f}%")
    dpg.set_value("status_text", "Monte Carlo selesai.")

def on_slider_change(sender, app_data, user_data):
    """Callback saat slider digerakkan."""
    param_name = user_data
    current_params[param_name] = app_data
    run_quick_simulation()

def on_checkbox_change(sender, app_data, user_data):
    current_params["anomaly_enabled"] = app_data
    run_quick_simulation()

# ============================================================
# MEMBANGUN UI
# ============================================================
dpg.create_context()

# Tema warna (opsional)
with dpg.theme() as global_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (30, 30, 30))
        dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (50, 50, 150))

dpg.bind_theme(global_theme)

# Window utama
with dpg.window(label="Skjold-9 Simulation Control Panel", width=WINDOW_WIDTH, height=WINDOW_HEIGHT, tag="main_window"):
    
    # ---- Grup Kiri: Kontrol ----
    with dpg.group(horizontal=True):
        with dpg.child_window(width=350, height=WINDOW_HEIGHT-50, tag="control_panel"):
            dpg.add_text("PARAMETER ASTEROID")
            dpg.add_separator()
            
            dpg.add_text("Posisi Awal (AU)")
            dpg.add_slider_float(label="X", default_value=DEFAULT_R_X, min_value=-3.0, max_value=3.0, 
                                 callback=on_slider_change, user_data="r_x", tag="slider_rx")
            dpg.add_slider_float(label="Y", default_value=DEFAULT_R_Y, min_value=-3.0, max_value=3.0, 
                                 callback=on_slider_change, user_data="r_y", tag="slider_ry")
            
            dpg.add_text("Kecepatan Awal (km/s)")
            dpg.add_slider_float(label="Vx", default_value=DEFAULT_V_X, min_value=-50.0, max_value=50.0, 
                                 callback=on_slider_change, user_data="v_x", tag="slider_vx")
            dpg.add_slider_float(label="Vy", default_value=DEFAULT_V_Y, min_value=-50.0, max_value=50.0, 
                                 callback=on_slider_change, user_data="v_y", tag="slider_vy")
            
            dpg.add_separator()
            dpg.add_text("ANOMALI TERSEMBUNYI")
            dpg.add_checkbox(label="Aktifkan Outgassing", default_value=DEFAULT_ANOMALY, 
                             callback=on_checkbox_change, tag="check_anomaly")
            dpg.add_slider_float(label="Kekuatan (x1e-7 m/s^2)", default_value=DEFAULT_ANOMALY_STRENGTH, 
                                 min_value=0.1, max_value=10.0, callback=on_slider_change, 
                                 user_data="anomaly_strength", tag="slider_anomaly")
            
            dpg.add_separator()
            dpg.add_text("SIMULASI")
            dpg.add_slider_int(label="Quick Estimate (N)", default_value=DEFAULT_QUICK_N, 
                               min_value=10, max_value=200, callback=on_slider_change, 
                               user_data="quick_n", tag="slider_quick_n")
            dpg.add_button(label="JALANKAN MONTE CARLO PENUH (N=500)", callback=run_full_monte_carlo, tag="btn_full_mc")
            
            dpg.add_separator()
            dpg.add_text("STATUS", tag="status_text", color=(255, 200, 100))
            dpg.add_text("Probabilitas: --%", tag="prob_text", color=(100, 255, 100))
        
        # ---- Grup Kanan: Visualisasi ----
        with dpg.child_window(width=1000, height=WINDOW_HEIGHT-50, tag="visualization_panel"):
            # Placeholder untuk plot (kita akan tambahkan plot Matplotlib nanti)
            dpg.add_text("VISUALISASI ORBIT & HISTOGRAM", color=(200, 200, 200))
            dpg.add_text("(Plot akan muncul di sini setelah backend dihubungkan)")
            
            # Plot orbit (untuk sekarang pakai drawing sederhana)
            with dpg.plot(label="Orbit Asteroid", width=900, height=400, tag="plot_orbit"):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="X (AU)", tag="x_axis")
                dpg.add_plot_axis(dpg.mvYAxis, label="Y (AU)", tag="y_axis")
                # Scatter Matahari
                dpg.add_scatter_series([0], [0], label="Matahari", parent="y_axis", tag="scatter_sun")
                # Scatter Bumi (posisi awal)
                dpg.add_scatter_series([1.0], [0.0], label="Bumi", parent="y_axis", tag="scatter_earth")
                # Lintasan asteroid (dummy)
                dpg.add_line_series([], [], label="Asteroid", parent="y_axis", tag="line_asteroid")
            
            # Histogram (placeholder)
            with dpg.plot(label="Distribusi Jarak Minimum", width=900, height=300, tag="plot_hist"):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="Jarak Minimum (AU)", tag="hist_x")
                dpg.add_plot_axis(dpg.mvYAxis, label="Frekuensi", tag="hist_y")

dpg.create_viewport(title='Skjold-9 Interactive Simulator', width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()