import os
import numpy as np
import matplotlib.pyplot as plt
from simulation.core.engine import SimulationEngine
from simulation.analytics.metrics import calculate_macro_metrics

def run_validation():
    # India 2024 targets
    TARGET_GINI = 0.35
    TARGET_TFR = 2.0
    TARGET_UNEMPLOYMENT = 0.07 # 7%
    
    print("Starting Anthropolis Validation Run (180 Ticks / 15 Years)...")
    
    engine = SimulationEngine(population_size=150, seed=42)
    # Using the tuned parameters for demonstration
    engine.parameters["cobb_douglas_alpha"] = 0.42
    engine.parameters["cobb_douglas_beta"] = 0.58
    engine.parameters["asfr_base_peak1"] = 122.9 / 12000.0
    
    ticks = 180
    
    gini_history = []
    tfr_history = []
    unemp_history = []
    time_axis = []
    
    for t in range(ticks):
        engine.step()
        metrics = calculate_macro_metrics(
            engine.citizens, 
            engine.nodes, 
            engine.dead_citizens,
            births_window=engine.births_history,
            infant_deaths_window=engine.infant_deaths_history
        )
        gini_history.append(metrics.get("gini_coefficient", 0.0))
        tfr_history.append(metrics.get("total_fertility_rate", 2.0))
        unemp_history.append(metrics.get("unemployment_rate", 0.0))
        time_axis.append(t)
        
        if (t + 1) % 12 == 0:
            print(f"Year {(t + 1) // 12} Completed. Gini: {gini_history[-1]:.3f} | TFR: {tfr_history[-1]:.2f} | Unemp: {unemp_history[-1]*100:.1f}%")

    # Plotting
    plt.style.use('dark_background')
    fig, axs = plt.subplots(3, 1, figsize=(10, 12))
    
    # 1. Gini
    axs[0].plot(time_axis, gini_history, color='#ff9999', lw=2, label='Simulated Gini')
    axs[0].axhline(y=TARGET_GINI, color='w', linestyle='--', label=f'World Bank Target ({TARGET_GINI})')
    axs[0].set_title('Wealth Inequality (Gini Coefficient)')
    axs[0].set_ylabel('Gini')
    axs[0].legend()
    axs[0].grid(True, alpha=0.2)
    
    # 2. TFR
    # Smooth TFR using a rolling 12-month average for visualization
    tfr_smoothed = np.convolve(tfr_history, np.ones(12)/12, mode='valid')
    tfr_time = time_axis[11:]
    axs[1].plot(tfr_time, tfr_smoothed, color='#99ff99', lw=2, label='Simulated TFR (12m rolling)')
    axs[1].axhline(y=TARGET_TFR, color='w', linestyle='--', label=f'World Bank Target ({TARGET_TFR})')
    axs[1].set_title('Total Fertility Rate (TFR)')
    axs[1].set_ylabel('Births per Woman')
    axs[1].legend()
    axs[1].grid(True, alpha=0.2)
    
    # 3. Unemployment
    axs[2].plot(time_axis, np.array(unemp_history)*100, color='#99ccff', lw=2, label='Simulated Unemployment')
    axs[2].axhline(y=TARGET_UNEMPLOYMENT*100, color='w', linestyle='--', label=f'World Bank Target ({TARGET_UNEMPLOYMENT*100}%)')
    axs[2].set_title('Unemployment Rate')
    axs[2].set_xlabel('Simulation Ticks (Months)')
    axs[2].set_ylabel('Unemployment %')
    axs[2].legend()
    axs[2].grid(True, alpha=0.2)
    
    plt.tight_layout()
    
    # Save to artifacts
    output_path = "/Users/namanjaswani/.gemini/antigravity-ide/brain/2ea6d925-08d7-4c95-b18f-1b1225d5a774/scratch/validation_results.png"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    print(f"\nValidation chart successfully generated: {output_path}")
    
    # Print final validation metrics
    print("\n--- Final Empirical Grounding vs World Bank Targets ---")
    print(f"Gini Coefficient: Simulated {gini_history[-1]:.3f} vs Target {TARGET_GINI:.3f}")
    final_tfr = tfr_smoothed[-1] if len(tfr_smoothed) > 0 else tfr_history[-1]
    print(f"Total Fertility Rate: Simulated {final_tfr:.2f} vs Target {TARGET_TFR:.2f}")
    print(f"Unemployment Rate: Simulated {unemp_history[-1]*100:.1f}% vs Target {TARGET_UNEMPLOYMENT*100:.1f}%")

if __name__ == "__main__":
    run_validation()
