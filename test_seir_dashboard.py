import pandas as pd
from simulation.core.engine import SimulationEngine
from simulation.analytics.metrics import calculate_macro_metrics

def main():
    engine = SimulationEngine(
        population_size=1467231210,
        initial_gov_capital=1270000000000.0,
        seed=None
    )
    
    print(f"Tick 0 - Citizens: {len(engine.citizens)}")
    metrics_t0 = calculate_macro_metrics(engine.citizens, engine.nodes, engine.dead_citizens)
    print(f"Tick 0 - Exposed: {metrics_t0['seir_exposed']}, Infected: {metrics_t0['seir_infected']}, Recovered: {metrics_t0['seir_recovered']}")
    
    for i in range(1, 21):
        engine.step()
        metrics = engine.history[-1]
        print(f"Tick {i} - E: {metrics['seir_exposed']}, I: {metrics['seir_infected']}, R: {metrics['seir_recovered']}")

if __name__ == "__main__":
    main()
