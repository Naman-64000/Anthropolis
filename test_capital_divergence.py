import pandas as pd
from simulation.core.engine import SimulationEngine
from simulation.analytics.metrics import calculate_macro_metrics

def main():
    engine = SimulationEngine(
        population_size=1467231210,
        initial_gov_capital=1270000000000.0,
        seed=None
    )
    
    for i in range(1, 181):
        engine.step()
        metrics = engine.history[-1]
        
        gov_cap = metrics['government_capital'] * engine.pop_scale
        priv_cap = metrics['private_capital'] * engine.pop_scale
        if i % 10 == 0:
            print(f"Tick {i} - Gov: ${gov_cap/1e9:,.2f}B, Private: ${priv_cap/1e9:,.2f}B")

if __name__ == "__main__":
    main()
