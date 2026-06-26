import sys
import numpy as np
from simulation.core.engine import SimulationEngine

def main():
    print("="*90)
    print("SUBSIDY & TAX DIAGNOSTIC (Avg across 5 seeds)")
    print("="*90)
    
    seeds = [42, 7, 2024, 1337, 99]
    ticks_to_record = [0, 30, 60, 90, 120, 150, 180]
    
    all_solvencies = {t: [] for t in ticks_to_record}
    
    # We will just run seed=42 for detailed breakdown of purchases
    engine = SimulationEngine(
        population_size=1467231210,
        initial_gov_capital=1_270_000_000_000.0,
        seed=42,
    )
    
    print(f"{'Tick':>4} | {'Groc Sub':>10} | {'Base Prc':>10} | {'Tax/Emp':>10} | {'C_Tax':>10} | {'Employed':>10} | {'Tot Groc Sub':>14}")
    
    for tick in range(1, 181):
        prev_gov_cap = engine.government_capital
        prev_spending = sum(c.total_spending for c in engine.citizens)
        
        # We need a way to count food purchases. 
        # But `citizen.py` does not track number of food purchases natively. 
        # So we approximate: grocery price is base_p_grocery * (1-0.8).
        # We can just look at the `base_p_grocery` in node "store_fresh".
        store = engine.get_node_by_id("store_fresh")
        base_p_grocery = (store.price if store else 20.0) * 20.0
        
        # Now using the fixed nominal subsidy
        subsidy_g = min(engine.grocery_subsidy_fixed, base_p_grocery)
        
        engine.step()
        
        employed_count = sum(1 for c in engine.citizens if c.is_employed)
        tax_per_emp = engine.tick_income_tax_inflow / employed_count if employed_count > 0 else 0.0
        
        if tick in ticks_to_record or tick == 1:
            print(f"{tick:>4} | {subsidy_g:>10,.2f} | {base_p_grocery:>10,.2f} | {tax_per_emp:>10,.2f} | {engine.tick_consumption_tax_inflow:>10,.2f} | {employed_count:>10} | {engine.tick_subsidy_outflow:>14,.2f}")
    
    print("\\nRunning Solvency Averages Across 5 Seeds...")
    for seed in seeds:
        engine_s = SimulationEngine(
            population_size=1467231210,
            initial_gov_capital=1_270_000_000_000.0,
            seed=seed,
        )
        all_solvencies[0].append(1.0)
        for tick in range(1, 181):
            engine_s.step()
            if tick in ticks_to_record:
                # the latest solvency is calculated in metrics
                solvency = engine_s.history[-1].get("fiscal_solvency", 1.0)
                all_solvencies[tick].append(solvency)
                
    print(f"\\n{'Tick':>5} | {'Avg Solvency':>15}")
    for t in ticks_to_record:
        avg_sol = np.mean(all_solvencies[t])
        print(f"{t:>5} | {avg_sol*100:>14.1f}%")

    print("\\n" + "="*90)
    print("DEBT SEEDING FIX DIAGNOSTIC")
    print("="*90)
    
    # Tick-0 Gini across 5 seeds
    gini_0 = []
    for seed in seeds:
        e = SimulationEngine(population_size=1467231210, initial_gov_capital=1_270_000_000_000.0, seed=seed)
        gini_0.append(e.history[-1]["gini_coefficient"])
        
    print(f"Tick-0 Gini across 5 seeds: {[round(g, 4) for g in gini_0]}")
    print(f"Average Tick-0 Gini: {np.mean(gini_0):.4f}")

if __name__ == "__main__":
    main()
