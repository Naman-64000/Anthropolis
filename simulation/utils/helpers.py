import random
import numpy as np
from typing import Dict, Any


def get_default_config() -> Dict[str, Any]:
    """Returns the default configuration values for initializing the simulation."""
    return {
        "population_size": 1467231210,
        "initial_gov_capital": 1270000000000.0,
        "seed": 2024,
    }


def format_report_summary(final_metrics: Dict[str, Any]) -> str:
    """Formats a dict of metrics into a readable string summary."""
    return f"""
=========================================
      SIMULATION RUN RESULTS
=========================================
Ticks Elapsed:           {final_metrics.get('tick', 0)}
Final Population:        {final_metrics.get('population', 0)} (Alive)
Accumulated Death Toll:  {final_metrics.get('death_toll', 0)}
Average Life Expectancy: {final_metrics.get('average_life_expectancy', 0.0):.2f} years

--- Macro-Economics ---
Average Bank Balance:    ${final_metrics.get('average_bank_balance', 0.0):.2f}
Average Household Debt:  ${final_metrics.get('average_debt', 0.0):.2f}
Gini Coefficient:        {final_metrics.get('gini_coefficient', 0.0):.4f} (Wealth Inequality)
Unemployment Rate:       {final_metrics.get('unemployment_rate', 0.0) * 100:.2f}%
Government Treasury:     ${final_metrics.get('government_capital', 0.0):.2f}
Private Capital Sum:     ${final_metrics.get('private_capital', 0.0):.2f}

--- Healthcare & Education ---
Average Citizen Health:  {final_metrics.get('average_health', 0.0):.2f}/70.8
Average Stress Level:    {final_metrics.get('average_stress', 0.0):.2f}/100
Hospital Bed Strain:     {final_metrics.get('hospital_strain', 0.0) * 100:.2f}%
Average Education Level: {final_metrics.get('average_education', 0.0) * 100:.2f}%
=========================================
"""
