import numpy as np
from simulation_engine import run_single_trajectory, run_monte_carlo

if __name__ == '__main__':
    # Tes satu simulasi
    print("Running single simulation test...")
    res = run_single_trajectory(r_x=-1.2, r_y=0.5, v_x=18.0, v_y=-4.5)
    print("Min distance (km):", res.min_distance_km)
    print("Impact:", res.impact)
    print("Specific Energy (J/kg):", res.orbital_energy)

    # Tes Monte Carlo
    print("\nRunning Monte Carlo test...")
    res2 = run_monte_carlo(r_x=-1.2, r_y=0.5, v_x=18.0, v_y=-4.5, n_sims=20)
    print("Probability (%):", res2.impact_probability)
    print("Sample trajectory count:", len(res2.sample_trajectories))