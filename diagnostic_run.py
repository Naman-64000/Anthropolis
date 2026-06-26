import sys
import numpy as np
from simulation.core.engine import SimulationEngine

def main():
    engine = SimulationEngine(
        population_size=1467231210,
        initial_gov_capital=1_270_000_000_000.0,
        seed=42,
    )
    
    print("="*90)
    print("GOVERNMENT TREASURY DIAGNOSTIC")
    print("="*90)
    print(f"{'Tick':>4} | {'Gov Cap':>14} | {'Corp Tax':>10} | {'Inc Tax':>10} | {'Welf/UBI':>10} | {'Hidden Subsidy':>14} | {'Bailout':>10} | {'Escheat':>10}")
    print("-" * 90)
    
    initial_gov_cap_scaled = engine.government_capital
    prev_gov_cap = initial_gov_cap_scaled
    cumulative_corp_tax = 0.0
    cumulative_inc_tax = 0.0
    cumulative_welfare_ubi = 0.0
    cumulative_bailout = 0.0
    cumulative_escheat = 0.0
    
    print(f"{0:>4} | {engine.government_capital:>14,.0f} | {0:>10,.0f} | {0:>10,.0f} | {0:>10,.0f} | {0:>14,.0f} | {0:>10,.0f} | {0:>10,.0f}")
    
    prev_escheat = engine.total_wealth_escheated
    
    for tick in range(1, 181):
        engine.step()
        
        cumulative_corp_tax += engine.tick_tax_inflow
        cumulative_inc_tax += getattr(engine, 'tick_income_tax_inflow', 0.0)
        cumulative_welfare_ubi += engine.tick_subsidy_outflow
        cumulative_bailout += engine.tick_public_bailout_total
        
        escheat_this_tick = engine.total_wealth_escheated - prev_escheat
        cumulative_escheat += escheat_this_tick
        prev_escheat = engine.total_wealth_escheated
        
        if tick % 30 == 0:
            expected = (initial_gov_cap_scaled + cumulative_corp_tax + cumulative_inc_tax + cumulative_escheat 
                        - cumulative_welfare_ubi - cumulative_bailout)
            hidden_subsidies = expected - engine.government_capital
            print(f"{tick:>4} | {engine.government_capital:>14,.0f} | {cumulative_corp_tax:>10,.0f} | {cumulative_inc_tax:>10,.0f} | {cumulative_welfare_ubi:>10,.0f} | {hidden_subsidies:>14,.0f} | {cumulative_bailout:>10,.0f} | {cumulative_escheat:>10,.0f}")

    print("\n" + "="*90)
    print("CUMULATIVE DIVIDEND SKEW DIAGNOSTIC (Ticks 1-180)")
    print("="*90)
    
    div_data = []
    for c in engine.citizens:
        if c.total_dividends_received > 0:
            div_data.append({
                "id": c.citizen_id,
                "edu": c.education_level,
                "bal": c.bank_balance,
                "div": c.total_dividends_received
            })
            
    div_data.sort(key=lambda x: x["div"], reverse=True)
    
    total_divs = sum(d["div"] for d in div_data)
    if total_divs == 0:
        print("No dividends paid at tick 180.")
    else:
        top_10_count = int(len(div_data) * 0.10)
        bottom_50_count = int(len(div_data) * 0.50)
        
        top_10_divs = sum(d["div"] for d in div_data[:top_10_count])
        bottom_50_divs = sum(d["div"] for d in div_data[-bottom_50_count:])
        
        print(f"Total employed receiving dividends: {len(div_data)}")
        print(f"Top 10% received: ${top_10_divs:,.2f} ({(top_10_divs/total_divs)*100:.1f}%)")
        print(f"Bottom 50% received: ${bottom_50_divs:,.2f} ({(bottom_50_divs/total_divs)*100:.1f}%)")
        print("\nTop 5 Recipients:")
        for i, d in enumerate(div_data[:5]):
            print(f"  {i+1}. Edu: {d['edu']:.4f} | Bank: ${d['bal']:,.2f} | Div: ${d['div']:,.2f}")
            
if __name__ == "__main__":
    main()
