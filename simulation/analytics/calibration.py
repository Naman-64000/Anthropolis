import numpy as np
from scipy.optimize import minimize
from simulation.core.engine import SimulationEngine
from simulation.analytics.metrics import calculate_macro_metrics

def run_simulation(params: np.ndarray, ticks: int = 180, seed: int = 42) -> dict:
    """
    Runs the simulation with the given parameter array.
    Parameter array mapping:
    [0]: cobb_douglas_alpha
    [1]: cobb_douglas_beta
    [2]: asfr_base_peak1
    [3]: gompertz_A_m multiplier (scales base mortality)
    """
    engine = SimulationEngine(population_size=150, seed=seed)
    
    # Inject parameters
    engine.parameters["cobb_douglas_alpha"] = float(params[0])
    engine.parameters["cobb_douglas_beta"] = float(params[1])
    engine.parameters["asfr_base_peak1"] = float(params[2])
    
    # Scale mortality bases
    base_A_m = 0.002
    base_A_f = 0.001
    engine.parameters["gompertz_A_m"] = base_A_m * float(params[3])
    engine.parameters["gompertz_A_f"] = base_A_f * float(params[3])
    
    # Run ticks
    for _ in range(ticks):
        engine.step()
        
    # Calculate metrics
    metrics = calculate_macro_metrics(
        engine.citizens,
        engine.nodes,
        engine.dead_citizens,
        births_window=engine.births_history,
        infant_deaths_window=engine.infant_deaths_history,
    )
    return metrics

def objective_function(params: np.ndarray) -> float:
    # India World Bank targets
    TARGET_GINI = 0.35         # Gini coefficient
    TARGET_TFR = 2.0           # Total Fertility Rate
    TARGET_UNEMPLOYMENT = 0.07 # 7% unemployment rate
    
    try:
        metrics = run_simulation(params)
    except Exception as e:
        # If simulation crashes, penalize heavily
        return 1e6
        
    gini = metrics.get("gini_coefficient", 0.0)
    tfr = metrics.get("total_fertility_rate", 2.0)
    unemployment = metrics.get("unemployment_rate", 0.0)
    
    error_gini = (gini - TARGET_GINI)**2
    error_tfr = (tfr - TARGET_TFR)**2
    error_unemployment = (unemployment - TARGET_UNEMPLOYMENT)**2
    
    # Alpha and Beta should sum to roughly 1.0 (constant returns to scale)
    error_scale = (params[0] + params[1] - 1.0)**2
    
    # Combine errors
    mse = error_gini + error_tfr + error_unemployment + error_scale
    
    print(f"Params: {params} -> MSE: {mse:.4f} (Gini: {gini:.3f}, TFR: {tfr:.2f}, Unemp: {unemployment:.3f})")
    return mse

def run_calibration():
    # Initial guess
    # [alpha, beta, asfr_peak1, mortality_mult]
    initial_guess = np.array([0.42, 0.58, 122.9/12000.0, 1.0])
    
    # Bounds for the parameters
    bounds = [
        (0.1, 0.9),      # alpha
        (0.1, 0.9),      # beta
        (0.001, 0.05),   # asfr
        (0.1, 5.0)       # mortality multiplier
    ]
    
    print("Starting calibration loop using Nelder-Mead...")
    result = minimize(
        objective_function, 
        initial_guess, 
        method='Nelder-Mead',
        bounds=bounds,
        options={'maxiter': 20, 'disp': True}
    )
    
    print("\nCalibration Complete!")
    print("Optimized Parameters:")
    print(f"Cobb-Douglas Alpha: {result.x[0]:.4f}")
    print(f"Cobb-Douglas Beta:  {result.x[1]:.4f}")
    print(f"ASFR Peak 1:        {result.x[2]:.6f}")
    print(f"Mortality Mult:     {result.x[3]:.4f}")
    print(f"Final MSE:          {result.fun:.6f}")

if __name__ == "__main__":
    run_calibration()
