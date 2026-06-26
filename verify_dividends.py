"""
verify_dividends.py
===================
Runs 5 independent 180-tick simulations (different seeds) to confirm the effect of
the new profit dividend distribution mechanism on:
  - Gini coefficient
  - Private capital
  - Citizen bank balance
  - Government treasury
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
    private_capital_values = []
    avg_bank_balance_values = []
    gov_treasury_values = []
    total_dividends = 0.0
    
    for tick in range(1, TICKS + 1):
        engine.step()
        latest = engine.history[-1]
        
        gini_values.append(latest.get("gini_coefficient", 0.0))
        private_capital_values.append(latest.get("private_capital", 0.0))
        
        # Calculate average bank balance of alive citizens
        alive = [c for c in engine.citizens if not c.is_dead]
        avg_bal = sum(c.bank_balance for c in alive) / len(alive) if alive else 0.0
        avg_bank_balance_values.append(avg_bal)
        
        gov_treasury_values.append(latest.get("government_capital", 0.0))
        total_dividends += latest.get("tick_dividends_paid", 0.0)
        
    return {
        "seed": seed,
        "gini_min": min(gini_values),
        "gini_max": max(gini_values),
        "gini_avg": sum(gini_values) / len(gini_values),
        "private_capital_final": private_capital_values[-1],
        "avg_bank_balance_final": avg_bank_balance_values[-1],
        "gov_treasury_final": gov_treasury_values[-1],
        "total_dividends": total_dividends
    }

def main():
    print("=" * 70)
    print("PROFIT DIVIDEND DISTRIBUTION VERIFICATION — 5 seeds × 180 ticks")
    print("=" * 70)
    
    all_results = []
    for seed in SEEDS:
        print(f"\\n▶  Running seed={seed} ...", flush=True)
        result = run_simulation(seed)
        all_results.append(result)
        
        print(f"   Gini Coefficient: min={result['gini_min']:.4f}, max={result['gini_max']:.4f}, avg={result['gini_avg']:.4f}")
        print(f"   Private Capital (Tick 180): ${result['private_capital_final']:,.2f}")
        print(f"   Avg Citizen Bank Balance (Tick 180): ${result['avg_bank_balance_final']:,.2f}")
        print(f"   Gov Treasury (Tick 180): ${result['gov_treasury_final']:,.2f}")
        print(f"   Total Dividends Paid: ${result['total_dividends']:,.2f}")
        
    print("\\n" + "=" * 70)
    print("SUMMARY (Averages across 5 seeds)")
    print("=" * 70)
    
    avg_gini = np.mean([r['gini_avg'] for r in all_results])
    avg_private_cap = np.mean([r['private_capital_final'] for r in all_results])
    avg_bank_bal = np.mean([r['avg_bank_balance_final'] for r in all_results])
    avg_gov = np.mean([r['gov_treasury_final'] for r in all_results])
    avg_divs = np.mean([r['total_dividends'] for r in all_results])
    
    print(f"  Average Gini: {avg_gini:.4f} (Previous was ~0.3846, expect slight reduction)")
    print(f"  Average Private Capital: ${avg_private_cap:,.2f} (Expect plateau, not climbing infinitely)")
    print(f"  Average Citizen Bank Balance: ${avg_bank_bal:,.2f} (Expect steeper upward slope)")
    print(f"  Average Gov Treasury: ${avg_gov:,.2f} (Expect relatively stable)")
    print(f"  Average Total Dividends Paid: ${avg_divs:,.2f}")
    
    print("\\n✅  Verification complete.")

if __name__ == "__main__":
    main()
