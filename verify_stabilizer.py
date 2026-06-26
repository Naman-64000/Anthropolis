"""
verify_stabilizer.py
===================
Runs 5 independent 180-tick simulations (different seeds) to confirm the effect of
the new fiscal stabilizer and sovereign debt tracking.
"""

import sys
import numpy as np
from simulation.core.engine import SimulationEngine

SEEDS = [42, 7, 2024, 1337, 99]
TICKS = 180

def run_simulation(seed: int) -> dict:
    engine = SimulationEngine(
        population_size=1467231210,
        initial_gov_capital=1_270_000_000_000.0,
        seed=seed,
    )
    
    gini_values = []
    gov_cap_values = []
    gov_debt_values = []
    solvency_values = []
    avg_citizen_debt_values = []
    total_c_tax = 0.0
    tick_1_deficit = 0.0
    
    for tick in range(1, TICKS + 1):
        engine.step()
        latest = engine.history[-1]
        
        if tick == 1:
            tick_1_deficit = engine.tick_tax_inflow - engine.tick_subsidy_outflow - engine.tick_public_bailout_total - engine.tick_sovereign_interest
            
        total_c_tax += engine.tick_consumption_tax_inflow
        
        gini_values.append(latest.get("gini_coefficient", 0.0))
        gov_cap_values.append(latest.get("government_capital", 0.0))
        gov_debt_values.append(latest.get("government_debt", 0.0))
        solvency_values.append(latest.get("fiscal_solvency", 1.0))
        
        alive = [c for c in engine.citizens if not c.is_dead]
        avg_debt = sum(c.debt for c in alive) / len(alive) if alive else 0.0
        avg_citizen_debt_values.append(avg_debt)
        
    return {
        "seed": seed,
        "gini_min": min(gini_values),
        "gini_max": max(gini_values),
        "gini_avg": sum(gini_values) / len(gini_values),
        "min_gov_cap": min(gov_cap_values),
        "final_gov_debt": gov_debt_values[-1],
        "min_solvency": min(solvency_values),
        "avg_citizen_debt_final": avg_citizen_debt_values[-1],
        "total_c_tax": total_c_tax,
        "tick_1_deficit": tick_1_deficit,
        "gini_tick_180": gini_values[-1]
    }

def main():
    print("=" * 70)
    print("FISCAL STABILIZER VERIFICATION — 5 seeds × 180 ticks")
    print("=" * 70)
    
    all_results = []
    for seed in SEEDS:
        print(f"\\n▶  Running seed={seed} ...", flush=True)
        result = run_simulation(seed)
        all_results.append(result)
        
        print(f"   Gini (Avg): {result['gini_avg']:.4f}")
        print(f"   Min Gov Cap: ${result['min_gov_cap']:,.2f}")
        print(f"   Final Gov Debt: ${result['final_gov_debt']:,.2f}")
        print(f"   Min Solvency: {result['min_solvency']*100:.1f}%")
        print(f"   Final Avg Citizen Debt: ${result['avg_citizen_debt_final']:,.2f}")
        
    print("\\n" + "=" * 70)
    print("SUMMARY (Averages across 5 seeds)")
    print("=" * 70)
    
    avg_gini = np.mean([r['gini_avg'] for r in all_results])
    min_gov_cap_all = min([r['min_gov_cap'] for r in all_results])
    avg_gov_debt = np.mean([r['final_gov_debt'] for r in all_results])
    min_solvency_all = min([r['min_solvency'] for r in all_results])
    avg_cit_debt = np.mean([r['avg_citizen_debt_final'] for r in all_results])
    avg_c_tax = np.mean([r['total_c_tax'] for r in all_results])
    avg_tick_1_deficit = np.mean([r['tick_1_deficit'] for r in all_results])
    avg_gini_180 = np.mean([r['gini_tick_180'] for r in all_results])
    
    print(f"  Average Gini: {avg_gini:.4f}")
    print(f"  Did Gov Cap stay >= 0? {'YES' if min_gov_cap_all >= 0 else 'NO'} (Min: ${min_gov_cap_all:,.2f})")
    print(f"  Average Gov Debt (Tick 180): ${avg_gov_debt:,.2f}")
    print(f"  Did Stabilizer Trigger? {'YES' if min_solvency_all < 0.8 else 'NO'} (Lowest Solvency: {min_solvency_all*100:.1f}%)")
    print(f"  Average Citizen Debt (Tick 180): ${avg_cit_debt:,.2f}")
    print(f"  Average Total Consumption Tax (180 Ticks): ${avg_c_tax:,.2f}")
    print(f"  Average Tick-1 Deficit (Tax - Spend): ${avg_tick_1_deficit:,.2f} {'(Surplus!)' if avg_tick_1_deficit >= 0 else '(Deficit)'}")
    print(f"  Average Gini (Tick 180): {avg_gini_180:.4f}")
    
    print("\\n✅  Verification complete.")

if __name__ == "__main__":
    main()
