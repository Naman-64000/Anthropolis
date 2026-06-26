from typing import List, Dict, Any
from simulation.core.citizen import Citizen
from simulation.core.environment import EnvironmentNode


def calculate_gini(values: List[float]) -> float:
    """
    Computes the Gini coefficient for a list of values.
    Gini ranges from 0 (perfect equality) to 1 (perfect inequality).
    Negative values are clamped to 0 to prevent Gini coefficients > 1.0.
    """
    if not values:
        return 0.0

    # Clamp negative values to 0 for standard Gini bounds
    clamped_values = sorted([max(0.0, v) for v in values])
    n = len(clamped_values)
    
    if n == 0 or sum(clamped_values) == 0:
        return 0.0

    sum_vals = sum(clamped_values)
    gini_sum = 0.0
    for i, val in enumerate(clamped_values):
        # 1-based index: i + 1
        gini_sum += (i + 1) * val

    return (2.0 * gini_sum) / (n * sum_vals) - (n + 1.0) / n


def calculate_macro_metrics(
    citizens: List[Citizen],
    nodes: List[EnvironmentNode],
    total_dead_citizens: List[Citizen],
    births_window: List[int] = None,
    infant_deaths_window: List[int] = None,
) -> Dict[str, Any]:
    """
    Aggregates data from individual citizens and environment nodes
    to compute macro-level system metrics on a single tick.
    """
    alive_citizens = [c for c in citizens if not c.is_dead]
    pop_size = len(alive_citizens)

    if pop_size == 0:
        return {
            "population": 0,
            "average_age": 0.0,
            "average_health": 0.0,
            "average_stress": 0.0,
            "average_bank_balance": 0.0,
            "average_debt": 0.0,
            "gini_coefficient": 0.0,
            "unemployment_rate": 0.0,
            "average_education": 0.0,
            "hospital_strain": 0.0,
            "death_toll": len(total_dead_citizens),
            "average_life_expectancy": 0.0,
            "seir_susceptible": 0,
            "seir_exposed": 0,
            "seir_infected": 0,
            "seir_recovered": 0,
            "infant_mortality": 26.0,
        }

    # Demographics & State Averages
    avg_age = sum(c.age for c in alive_citizens) / pop_size
    avg_health = sum(c.health for c in alive_citizens) / pop_size
    avg_stress = sum(c.stress_level for c in alive_citizens) / pop_size
    avg_bank = sum(c.bank_balance for c in alive_citizens) / pop_size
    avg_debt = sum(c.debt for c in alive_citizens) / pop_size
    avg_edu = sum(c.education_level for c in alive_citizens) / pop_size

    # Wealth Gini (using net worth of adults)
    adult_net_worth = [c.net_worth for c in alive_citizens if c.age >= 18.0]
    gini = calculate_gini(adult_net_worth)

    # Unemployment rate: unemployed citizens / labor force
    # Labor force = Citizens aged 18 to 65 who are not full-time students
    labor_force = [
        c for c in alive_citizens 
        if 18.0 <= c.age < 65.0 and not c.is_student
    ]
    unemployed = [c for c in labor_force if not c.is_employed and not getattr(c, "is_informal", False)]
    unemployment_rate = (
        len(unemployed) / len(labor_force) if labor_force else 0.0
    )

    informal_workers = [c for c in labor_force if getattr(c, "is_informal", False)]
    total_employed_count = len([c for c in labor_force if c.is_employed]) + len(informal_workers)
    informal_share = len(informal_workers) / total_employed_count if total_employed_count > 0 else 0.0

    # Hospital strain: occupied capacity vs total capacity across all hospitals
    hospitals = [n for n in nodes if n.node_type == "Hospital"]
    total_beds = sum(h.capacity for h in hospitals)
    occupied_beds = sum(h.occupied_slots for h in hospitals)
    hospital_strain = (
        occupied_beds / total_beds if total_beds > 0 else 0.0
    )

    # Life Expectancy (average age at death of all citizens who have died)
    death_toll = len(total_dead_citizens)
    avg_life_exp = (
        sum(c.age for c in total_dead_citizens) / death_toll
        if death_toll > 0
        else 0.0
    )

    # Infant Mortality Rate (Trailing rolling 12-tick window if available, fallback otherwise)
    if births_window is not None and infant_deaths_window is not None:
        total_births_window = sum(births_window)
        total_infant_deaths_window = sum(infant_deaths_window)
        if total_births_window == 0:
            infant_mortality = 26.0 + (hospital_strain * 10.0)
        else:
            infant_mortality = (total_infant_deaths_window / total_births_window) * 1000.0
    else:
        # Fallback to cumulative since start
        infant_deaths = sum(1 for c in total_dead_citizens if c.age < 1.0)
        births = sum(1 for c in citizens if c.citizen_id >= 1000) + sum(1 for c in total_dead_citizens if c.citizen_id >= 1000)
        
        # If no births yet, default to ~26 per 1000, influenced slightly by hospital strain
        if births == 0:
            infant_mortality = 26.0 + (hospital_strain * 10.0)
        else:
            infant_mortality = (infant_deaths / births) * 1000.0

    # Total Fertility Rate (Empirical calculation based on recent births)
    women_15_to_49 = [c for c in alive_citizens if c.sex == 'F' and 15.0 <= c.age < 50.0]
    if births_window is not None and len(women_15_to_49) > 0:
        # TFR = (Births per year / Women 15-49) * 35 (reproductive span)
        annual_births = sum(births_window)
        tfr = (annual_births / len(women_15_to_49)) * 35.0
    else:
        tfr = 2.0  # Default assumed if no data yet

    # SEIR Epidemiological counts
    s_count = sum(1 for c in alive_citizens if c.seir_state == 'S')
    e_count = sum(1 for c in alive_citizens if c.seir_state == 'E')
    i_count = sum(1 for c in alive_citizens if c.seir_state == 'I')
    r_count = sum(1 for c in alive_citizens if c.seir_state == 'R')

    return {
        "population": pop_size,
        "average_age": avg_age,
        "average_health": avg_health,
        "average_stress": avg_stress,
        "average_bank_balance": avg_bank,
        "average_debt": avg_debt,
        "gini_coefficient": gini,
        "unemployment_rate": unemployment_rate,
        "informal_employment_share": informal_share,
        "average_education": avg_edu,
        "hospital_strain": hospital_strain,
        "death_toll": death_toll,
        "average_life_expectancy": avg_life_exp,
        "seir_susceptible": s_count,
        "seir_exposed": e_count,
        "seir_infected": i_count,
        "seir_recovered": r_count,
        "infant_mortality": infant_mortality,
        "total_fertility_rate": tfr,
    }
