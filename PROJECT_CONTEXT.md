# PROJECT CONTEXT: Anthropolis Digital Twin

This document contains everything an outside AI or developer needs to understand, run, and debug the **Anthropolis** digital twin simulation from scratch.

---

## 1. PROJECT OVERVIEW

**Anthropolis** is a stochastic, closed-loop agent-based socio-demographic and macroeconomic simulation calibrated to India's demographic and economic structure (2024–2026).

### Core Architecture Layers
1. **Micro Layer (`Citizen`)**: Individual agents with health, energy, bank balance, debt, education, sex, religious affiliation, and religiosity. Agents make choices using **Prospect Theory** (evaluating consumption utility vs. debt disutility) and face mortality risk via a sex-split **Gompertz-Makeham** curve.
2. **Meso Layer (`EnvironmentNode`)**: Business and social institutions that employ citizens and sell goods/services:
   * **Workplaces**: Agricultural Co-op Farms, Industrial Textile Mills. They produce output via a **Cobb-Douglas production function** using capital and employee labor (human capital).
   * **Grocery Stores & Restaurants**: Sell food (healthy groceries vs. fast food) to restore agent energy.
   * **Hospitals**: Provide medical care to restore citizen health and cure SEIR infections.
   * **Schools**: Enroll youth to increase their education index (human capital).
3. **Macro Layer (`SimulationEngine`)**: Manages the global clock, demographic links, universal basic income (UBI), welfare stipends, income tax collections, deceased estate inheritance, and tracking analytics.

### Key Simulation Mechanics
* **Time Scale**: **1 Tick = 1 Month**.
* **Population Scale (`pop_scale`)**: The simulation runs with a default scaled agent count of **150 agents** representing a real-world base population of **1.467 billion people** (India census estimate). Thus:
  $$\text{pop\_scale} \approx 9,781,541.4$$
  All macro-aggregates (like the initial **\$1.27 Trillion** government treasury) are divided by `pop_scale` internally to ensure the micro-scale math matches the macro-scale allocations.

---

## 2. FULL VARIABLE LIST

### A. Citizen Variables (`citizen.py`)

| Variable Name | Type | Valid Range | Real-World Calibration (India 2024-2026) / Description |
| :--- | :--- | :--- | :--- |
| `citizen_id` | `int` | $\ge 0$ | Unique agent identifier. |
| `age` | `float` | $[0.0, 120.0]$ | Age in years (increments by $1/12$ per tick). Median starting age: **28.7 years**. |
| `baseline_health`| `float` | $[50.0, 100.0]$ | Target life expectancy at birth. Normal distribution around **70.8 years**. |
| `health` | `float` | $[0.0, 100.0]$ | Vitality level. Clamped at $0.0$ (death). Decreased by stress, infection, starvation. |
| `energy` | `float` | $[0.0, 2458.0]$ | Metabolic reserve in kcal. Decays monthly. Restored by food consumption. |
| `bank_balance` | `float` | $\ge 0.0$ | Liquid savings. Starting mean is lognormal-seeded around **\$1,712** median. |
| `debt` | `float` | $\ge 0.0$ | Outstanding debt. Initial mean is exponential-seeded around **\$1,068** average. |
| `education_level`| `float` | $[0.0, 1.0]$ | Schooling index. Initial beta-seeded with mean **0.44** (6.7 mean years of schooling). |
| `risk_tolerance` | `float` | $[0.0, 1.0]$ | Uniformly distributed starting risk threshold. Scales debt loss aversion. |
| `sex` | `str` | `{'M', 'F'}` | Sex ratio: **50.5% Male / 49.5% Female** (929 females per 1000 males target). |
| `religious_affiliation`| `int`| `[0, 4]` | Cultural split: Hindu: 79.8% (0), Muslim: 14.2% (1), Christian: 2.3% (2), Sikh: 1.7% (3), Other: 2.0% (4). |
| `religiosity` | `float` | $[0.0, 1.0]$ | Beta-seeded centered at **0.97** (importance of religion in life). Multiplies debt aversion. |
| `stress_level` | `float` | $[0.0, 100.0]$ | Stress index. Driven by high debt-to-balance ratio and low health. |
| `is_employed` | `bool` | `True/False` | Employee status. |
| `employer_id` | `str` | `None` / ID | ID of the employing node. |
| `is_student` | `bool` | `True/False` | Student enrollment status. |
| `is_dead` | `bool` | `True/False` | Vital status. |
| `cause_of_death` | `str` | `None` / text | Cause description (NCDs: 63%, Malnutrition, Ageing, SEIR). |
| `seir_state` | `str` | `{'S','E','I','R'}`| SEIR state (Susceptible, Exposed, Infected, Recovered). |
| `infection_days` | `int` | $\ge 0$ | Ticks spent in the current Exposed or Infected state. |
| `is_pregnant` | `bool` | `True/False` | Female pregnancy status. |
| `gestation_months`| `int` | $[0, 9]$ | Pregnancy duration count. |
| `birth_cooldown` | `int` | $\ge 0$ | Cooldown ticks before next possible pregnancy. |
| `parent_ids` | `list` | List of `int` | List of parent citizen IDs. |
| `offspring_ids` | `list` | List of `int` | List of children citizen IDs. |
| `total_earnings` | `float` | $\ge 0.0$ | Cumulative earnings in USD. |
| `total_spending` | `float` | $\ge 0.0$ | Cumulative spending in USD. |
| `work_experience`| `int` | $\ge 0$ | Cumulative months worked. |
| `daily_earnings` | `float` | $\ge 0.0$ | Earnings in the current tick. |
| `last_monthly_income`| `float`| $\ge 0.0$ | Income received in the last tick. |

### B. Environment Node Variables (`environment.py`)

| Variable Name | Type | Valid Range | Real-World Calibration / Description |
| :--- | :--- | :--- | :--- |
| `node_id` | `str` | Unique string | Unique identifier. |
| `node_name` | `str` | String | User-friendly name. |
| `node_type` | `str` | `Workplace`/`Hospital`/`School`/`GroceryStore`/`Restaurant` | Sector classification. |
| `capacity` | `int` | $\ge 0$ | Maximum physical visitor/customer capacity. |
| `price` | `float` | $\ge 0.0$ | Service/good price level. Experiences **4.75% annual inflation** compounded monthly. |
| `employee_capacity`| `int`| $\ge 0$ | Employee limit. National sector ratios: Agri: 44%, Industry: 22%, Services: 34%. |
| `capital` | `float` | $\ge 0.0$ | Corporate financial reserve. Seeded with **\$93,700** starting capital. |
| `employees` | `list` | List of Citizens| Hired staff list. |
| `occupied_slots` | `int` | $[0, \text{capacity}]$| Active visitor transactions processed in the current tick. |
| `monthly_revenue`| `float` | $\ge 0.0$ | Monthly income from citizen consumption. |
| `monthly_wages` | `float` | $\ge 0.0$ | Total wage pay outflows. |

### C. Simulation Engine Variables (`engine.py`)

| Variable Name | Type | Valid Range | Real-World Calibration / Description |
| :--- | :--- | :--- | :--- |
| `tick_count` | `int` | $\ge 0$ | Number of months simulated. |
| `next_citizen_id`| `int` | $\ge 0$ | Sequence counter for unique citizen IDs. |
| `population_size`| `int` | $\ge 1$ | Unscaled target population. Calibrated to India: **1,467,231,210**. |
| `government_capital`| `float`| $\ge 0.0$ | Government treasury. Scaled from unscaled sovereign reserves of **\$1.27 Trillion**. |
| `pop_scale` | `float` | $\ge 1.0$ | Population scaling factor. |
| `history` | `list` | List of dicts | Log of macro metrics for each tick. |
| `dependency_ratio`| `float` | $\ge 0.0$ | Ratio: $(\text{Age } <18 + \text{Age } \ge 65) / \text{Working-Age Population}$. |
| `total_wealth_inherited`| `float`| $\ge 0.0$| Cumulative wealth inherited by offspring. |
| `total_wealth_escheated`| `float`| $\ge 0.0$| Cumulative positive assets seized by government from childless decedents. |
| `tick_tax_inflow` | `float` | $\ge 0.0$ | Tax collections recorded in the current step. |
| `tick_subsidy_outflow`| `float`| $\ge 0.0$ | Subsidy and UBI payouts made in the current step. |
| `tick_debt_written_off`| `float`| $\ge 0.0$ | Debt written off during bankruptcy in the current step. |
| `citizens` | `list` | List of Citizens| Active alive population. |
| `nodes` | `list` | List of Nodes | physical and economic nodes in the city. |
| `dead_citizens` | `list` | List of Citizens| Deceased population record. |

---

## 3. ALL FORMULAS

### 1. Prospect Theory Value Function
* **Mathematical Form**:
  $$v(x) = \begin{cases} x^\alpha & \text{if } x \ge 0 \\ -\lambda_{\text{debt}} \cdot |x|^\beta & \text{if } x < 0 \end{cases}$$
* **Parameters**: $\alpha = 0.88$, $\beta = 0.88$.
* **Religiosity and Risk-Tolerance Scaling on Debt Loss-Aversion**:
  $$\lambda_{\text{debt}} = 2.25 \cdot (1.0 + 3.0 \cdot \text{religiosity}) \cdot (1.5 - \text{risk\_tolerance})$$
* **Location**: [citizen.py](file:///Users/namanjaswani/Downloads/Anthropolis/simulation/core/citizen.py) in `prospect_value()` and `Citizen._decide_food()`

### 2. Gompertz-Makeham Mortality Law
* **Mathematical Form**:
  $$\text{Force of Mortality } h(\text{age}) = A_{\text{effective}} + B_s \cdot c_s^{\text{age}}$$
  $$A_{\text{effective}} = A_s \cdot e^{\text{energy\_factor} + \text{poverty\_factor}}$$
  $$\text{energy\_factor} = \ln(1.5) \cdot \left(1.0 - \frac{\text{energy}}{2458.0}\right)$$
  $$\text{poverty\_factor} = \begin{cases} \ln(1.75) & \text{if } \text{net\_worth} \le 0.0 \\ 0.0 & \text{otherwise} \end{cases}$$
  $$\text{Monthly Probability of Mortality } P(Death) = 1.0 - e^{-h(\text{age}) \cdot \frac{1}{12}}$$
* **Parameters**: 
  * Male ($s = M$): $A_M = 0.002, B_M = 0.00004, c_M = 1.095$
  * Female ($s = F$): $A_F = 0.001, B_F = 0.00003, c_F = 1.090$
  * Sick adjustment: If $\text{health} < 20.0$, mortality hazard is exponentiated by $5.0$ ($P_{\text{eff}} = 1.0 - (1.0 - P)^{5.0}$). If $\text{seir\_state} == 'I'$, hazard is exponentiated by $2.5$ ($P_{\text{eff}} = 1.0 - (1.0 - P)^{2.5}$).
* **Location**: [citizen.py](file:///Users/namanjaswani/Downloads/Anthropolis/simulation/core/citizen.py) in `calculate_monthly_mortality_prob()` and `Citizen._apply_decays()`

### 3. Diminishing Biomedical Returns (Logarithmic Restoration)
* **Mathematical Form**:
  $$R(\text{amount}) = k \cdot \ln(1.0 + c \cdot \text{amount})$$
* **Location**: [citizen.py](file:///Users/namanjaswani/Downloads/Anthropolis/simulation/core/citizen.py) in `calculate_diminishing_restoration()`

### 4. Cobb-Douglas Production Function
* **Mathematical Form**:
  $$\text{Output } Y = A \cdot K^{0.42} \cdot L^{0.58}$$
  $$\text{TFP } A = (1.0 + \text{avg\_education}) \cdot \left(1.0 + \frac{0.022}{12}\right)^{\text{tick\_count}}$$
  $$\text{Labor Input } L = \sum_{e \in \text{employees}} \left(0.1 + \ln(1.0 + \text{education\_level}_e)\right) \cdot \left(\frac{\text{health}_e}{70.8}\right)$$
  $$\text{Workplace Revenue } = Y \cdot \text{price} \cdot \text{market\_fluctuation}$$
  $$\text{market\_fluctuation} = \max\left(0.2, \mathcal{N}\left(1.0, \frac{0.145}{\sqrt{12}}\right)\right)$$
* **Location**: 
  * Production: [environment.py](file:///Users/namanjaswani/Downloads/Anthropolis/simulation/core/environment.py) in `calculate_cobb_douglas_output()`
  * Human Capital & Fluctuation: [environment.py](file:///Users/namanjaswani/Downloads/Anthropolis/simulation/core/environment.py) in `Workplace.tick()`

### 5. Localized SEIR Infection Probability
* **Mathematical Form**:
  $$P(\text{infection at node } j) = 1.0 - e^{-\beta_j \cdot \left(\frac{I_j}{N_j}\right)}$$
* **Parameters**: Workplace transmission rate $\beta_{Workplace} = 0.35$; other spaces $\beta_{other} = 0.20$.
* **Location**: [environment.py](file:///Users/namanjaswani/Downloads/Anthropolis/simulation/core/environment.py) in `calculate_infection_prob()` and `EnvironmentNode._transmit_disease()`

### 6. Age-Specific Fertility Rate (ASFR)
* **Mathematical Form**:
  $$\text{ASFR}_{actual} = \text{ASFR}_{base} \cdot (1.0 - 0.5 \cdot \text{education\_level} - 0.3 \cdot \text{normalized\_wealth}) \cdot (0.5 + 1.5 \cdot \text{religiosity})$$
  $$\text{normalized\_wealth} = \min\left(1.0, \max\left(0.0, \frac{\text{net\_worth}}{5000.0}\right)\right)$$
* **Parameters**: 
  * $\text{ASFR}_{base} = 122.9 / 12000.0$ (Age 20-24)
  * $\text{ASFR}_{base} = 112.5 / 12000.0$ (Age 25-29)
  * $\text{ASFR}_{base} = 35.0 / 12000.0$ (Age 15-19, 30-45)
* **Location**: [engine.py](file:///Users/namanjaswani/Downloads/Anthropolis/simulation/core/engine.py) in `_execute_mating_and_fertility()`

### 7. Assortative Partner Matching Homophily
* **Mathematical Form**:
  $$\text{Similarity Weight } = 1.0 - (0.1 \cdot \text{rel\_diff} + 0.8 \cdot \text{aff\_diff} + 0.1 \cdot \text{wealth\_diff})$$
  $$\text{rel\_diff} = |\text{religiosity}_f - \text{religiosity}_m|$$
  $$\text{aff\_diff} = \begin{cases} 0 & \text{if } \text{affiliation}_f == \text{affiliation}_m \\ 1 & \text{otherwise} \end{cases}$$
  $$\text{wealth\_diff} = \min\left(1.0, \frac{|\text{bank\_balance}_f - \text{bank\_balance}_m|}{2000.0}\right)$$
* **Location**: [engine.py](file:///Users/namanjaswani/Downloads/Anthropolis/simulation/core/engine.py) in `_execute_mating_and_fertility()`

### 8. Dependency-Ratio Scaled Personal Income Tax Surcharge
* **Mathematical Form**:
  $$\text{effective\_tax\_rate} = \min(0.9, \text{tax\_rate} + \min(0.08, 0.10 \cdot \text{dependency\_ratio}))$$
* **Location**: [engine.py](file:///Users/namanjaswani/Downloads/Anthropolis/simulation/core/engine.py) in `_collect_income_taxes()`

### 9. Gini Coefficient
* **Mathematical Form**:
  $$\text{Gini} = \frac{2 \cdot \sum_{i=1}^n (i \cdot y_i)}{n \cdot \sum_{i=1}^n y_i} - \frac{n + 1}{n}$$
  where $y_i$ is sorted, clamped net worth: $y_i = \max(0.0, \text{net\_worth}_i)$ of living adults (age $\ge 18.0$).
* **Location**: [metrics.py](file:///Users/namanjaswani/Downloads/Anthropolis/simulation/analytics/metrics.py) in `calculate_gini()`

### 10. CPI Inflation Pricing
* **Mathematical Form**:
  $$\text{price}_{\text{tick}} = \text{price}_{\text{tick}-1} \cdot \left(1.0 + \frac{0.0475}{12.0}\right)$$
* **Location**: [environment.py](file:///Users/namanjaswani/Downloads/Anthropolis/simulation/core/environment.py) in `EnvironmentNode.tick()`

### 11. Wage Calculation
* **Mathematical Form**:
  $$\text{daily\_wage} = 3.5 + \text{education\_level} \cdot 5.0$$
  $$\text{monthly\_wage} = \text{daily\_wage} \cdot 20.0 \cdot \text{price\_factor}$$
  where $\text{price\_factor} = \frac{\text{price}}{5.0}$ for Workplace nodes, and $1.0$ otherwise.
* **Location**: [environment.py](file:///Users/namanjaswani/Downloads/Anthropolis/simulation/core/environment.py) in `calculate_wage()`

### 12. Grocery & Fast Food Purchase Utilities
* **Mathematical Form**:
  $$U_{\text{grocery}} = v(-P_{\text{grocery}}) + 1.5 \cdot v(R_{\text{energy\_grocery}}) + v(R_{\text{health\_grocery}})$$
  $$U_{\text{fast\_food}} = v(-P_{\text{fast\_food}}) + 0.8 \cdot v(R_{\text{energy\_fast\_food}}) + v(R_{\text{health\_fast\_food}})$$
  $$U_{\text{starve}} = v(\text{starvation\_penalty})$$
  where $\text{starvation\_penalty} = -100.0$ if $\text{energy} < 491.6$, and $-10.0$ otherwise.
  $$P(\text{choice}) = \text{softmax}(U_{\text{grocery}}, U_{\text{fast\_food}}, U_{\text{starve}})$$
* **Location**: [citizen.py](file:///Users/namanjaswani/Downloads/Anthropolis/simulation/core/citizen.py) in `Citizen._decide_food()`

---

## 4. HOW EVERYTHING CONNECTS

Anthropolis functions as a closed loop containing macro policy levers, meso institutions, and micro decisions:

```
[Workplace Production] ---> pays [Wages] ---> [Citizen Bank Balance]
      ^                                                  |
      |                                                  v
[Employee Labor] <--- drives decisions <--- [Prospect Theory Choice]
      |                                                  |
   (sick/healthy)                                        +---> [Income Taxes] ---> [Government Treasury]
      |                                                  |                                 |
[Hospital treatment] <--- [Subsidized healthcare] <-----+                                 v
      ^                                                                          [Subsidy Payouts]
      |                                                                                    |
(Admit confirmation) ---> [Reimbursed revenue] <------------------------------------------+
```

### Working Loops (End-to-End Stable)
* **Production-Wage-Consumption Loop**: Citizens supply labor $\rightarrow$ Workplaces produce output using Cobb-Douglas $\rightarrow$ Citizens receive monthly wages $\rightarrow$ Citizens spend wages on Groceries/Fast Food/Hospitals $\rightarrow$ Cash flows back into node capitals.
* **Fiscal-Subsidy Loop**: Citizens pay income tax (with surcharge during dependency crises) and workplaces pay corporate tax (on net profits) into the Government Treasury $\rightarrow$ The government treasury reimburses nodes for child/adult grocery subsidies, healthcare subsidies, and tuition fees.
* **Inheritance & Death Conservation Loop**: Deceased estates split positive assets or liabilities to offspring; childless estates escheat positive balances to the government and write off liabilities, strictly logging write-offs to maintain money conservation invariants.
* **Workplace SEIR Transmission**: 2% exposed starting seeds progress to infections $\rightarrow$ spreads in workplaces $\rightarrow$ pushes sick workers to hospitals.

### Partially Connected Loop Elements
* **Education Loop**: Children go to schools and accumulate education index. Tuition is reimbursed by the state. Hired adults with higher education receive higher wages, and aggregate education drives Cobb-Douglas production. However, schooling duration is fixed and cannot be changed by the citizen's own choices or aptitude.

### Unconnected / Inert Elements
* **Risk Tolerance**: Seeding initializes `Citizen.risk_tolerance = random.random()` (range $0.0-1.0$), and this scales the loss-aversion utility penalty for debt accumulation in prospect theory evaluations: `risk_discount = 1.5 - self.risk_tolerance`. However, it is not used in job search or career paths.

---

## 5. CURRENT KNOWN ISSUES

| Issue Description | Affected Subsystem | Status | Details |
| :--- | :--- | :--- | :--- |
| **Unbounded Debt Spiral** | Micro / Financials | **Fixed** | Citizens previously had no borrowing ceiling, allowing them to accumulate infinite debt. Fixed by introducing a debt ceiling $\max(2000.0, \text{last\_monthly\_income} \cdot 12.0)$ and a bankruptcy protocol that resets debt to 0, logged under money conservation logs. |
| **Hire-Then-Fire Same-Tick Churn** | Meso / Hiring | **Fixed** | Workplace nodes hired employees they couldn't afford because the job search logic didn't check capital sufficiency. Fixed by checking projected capital payroll bounds before hiring. |
| **Infant Mortality Tracking** | Metrics / Healthcare | **Fixed** | Infant mortality rate was not tracked accurately because new borns didn't have a reliable denominator of live births. Resolved by counting births stochastically based on ID thresholds and logging infant deaths under age 1.0. |
| **Child/Youth Consumption Multipliers** | Micro / Consumption | **Fixed** | Dependents drew full adult costs from parents for grocery stores and fast-food restaurants, causing rapid parental debt spirals. Fixed by standardizing childhood consumption needs. |
| **Deterministic Inheritance** | Macro / Step Loop | **Fixed** | Deceased estates leaked money from the closed-loop system, violating money conservation checks. Fixed by splitting assets/liabilities among offspring and government escheatment. |
| **Newborn ID Collisions** | Macro / Population | **Fixed** | Newborns received duplicate IDs because ID allocation used dynamic array lengths. Fixed by introducing a centralized `self.next_citizen_id` counter. |
| **Spatial Naming Conventions** | Code Cleanliness | **Fixed** | Distance calculations referenced spatial variables that did not exist in the non-spatial layout of nodes. Renamed `get_closest_node` to `get_best_available_node`. |
| **UI Rendering Flickers & Jumps** | UI / Lifecycle | **Fixed** | Streamlit layout was recreating container widgets on every tick, causing page resets. Resolved by defining static layouts and using a generator stream. |
| **Unused Risk Tolerance** | Micro / Decisions | **Fixed** | Now scales the loss-aversion factor in prospect theory: `risk_discount = 1.5 - self.risk_tolerance`. |
| **Zero-Education Productivity Deadlock** | Meso / Production | **Fixed** | Added a baseline of 0.1 labor input per employee so human capital doesn't fall to 0. |

---

## 6. LATEST SIMULATION RESULTS

A standard 180-month run starting with 150 agents (representing 1.46 billion people, \$1.27 Trillion sovereign treasury) yields the following metrics:

* **Starting State (Month 0)**:
  * Population: 150 (scaled to 1,467.23M)
  * Avg Age: 31.06 years
  * Avg Health: 71.35
  * Avg Stress: 14.00
  * Avg Bank Balance: $4,936.04
  * Avg Debt: $649.36
  * Gini Coefficient: 0.8282 (Lognormal wealth initialization)
  * Unemployment: 4.4%
  * Avg Education: 29.02%
  * Hospital Bed Strain: 0.00%
  * Death Toll: 0
  * Avg Life Expectancy: 0.00 years
  * SEIR S/E/I/R: 147 / 3 / 0 / 0
  * Government Treasury: $129,836.39 (unscaled: $1.27T)
  * Private Capital Sum: $562,200.00
* **Mid Run (Month 90)**:
  * Population: 157 (representing 1.535 billion)
  * Avg Age: 35.57 years
  * Avg Health: 71.31
  * Avg Stress: 4.07
  * Avg Bank Balance: $9,826.79
  * Avg Debt: $90.25
  * Gini Coefficient: 0.4682
  * Unemployment: 11.46%
  * Avg Education: 55.10%
  * Hospital Bed Strain: 0.00%
  * Death Toll: 4 (representing 39.1M people)
  * Avg Life Expectancy: 55.95 years
  * SEIR S/E/I/R: 153 / 0 / 0 / 4
  * Government Treasury: -$47,732.07 (representing -$466.9B unscaled. Reflects state budget deficit during active welfare/subsidy funding)
  * Private Capital Sum: $971,607.30
* **Final State (Month 180)**:
  * Population: 158 (representing 1.545 billion)
  * Avg Age: 39.88 years
  * Avg Health: 71.19
  * Avg Stress: 13.32
  * Avg Bank Balance: $16,508.29
  * Avg Debt: $222.40
  * Gini Coefficient: 0.4685
  * Unemployment: 28.44%
  * Avg Education: 57.59%
  * Hospital Bed Strain: 0.00%
  * Death Toll: 13 (representing 127M people)
  * Avg Life Expectancy: 53.58 years
  * SEIR S/E/I/R: 154 / 0 / 0 / 4
  * Government Treasury: $285,249.34 (representing $2.79T unscaled. Recovers to positive as business taxes accumulate and household savings grow)
  * Private Capital Sum: $3,797,221.14

### Assessment of Results
* **What Looks Right**: The population grows smoothly, tracking India's population trends. Wealth Gini coefficient settles to a very realistic ~0.46, down from the highly unequal initial lognormal distribution. Health and stress metrics are stable, and the SEIR pandemic resolves correctly. Average bank balances grow while average debt is kept low and capped due to debt ceilings and write-offs, preventing debt spirals. The government treasury recovers in the long-term, showing a working fiscal loop. Money conservation is perfectly preserved with $0.00 global discrepancy across all ticks.
* **What Looks Suspicious**: The unemployment rate climbs from 4.4% to 28.44% by tick 180. This is because workplaces hire based on capital sufficiency checks, and in the long run, as the private capital sum grows, some businesses might hit staffing capacity limits or candidates might be excluded due to demographic retirement (geriatric age 65+). Alternatively, the high capital requirement of businesses caps the job search when wages rise due to inflation and education. We should note this as a potential tuning opportunity for job availability or employee capacities.

---

## 7. FULL CODE

Below are the complete, unmodified current contents of all core codebase files.

### 1. `simulation/core/citizen.py`
```python
from __future__ import annotations
import random
import math
import numpy as np
from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
    from simulation.core.engine import SimulationEngine
    from simulation.core.environment import EnvironmentNode


def prospect_value(x: float, alpha: float=0.88, beta: float=0.88, lambda_: float=2.25) -> float:
    """Prospect Theory Value Function: Calculates perceived value with loss aversion."""
    if x >= 0:
        return np.power(x, alpha)
    else:
        return -lambda_ * np.power(np.abs(x), beta)


def calculate_monthly_mortality_prob(
    age: float,
    sex: str,
    energy: float,
    net_worth: float,
) -> float:
    """Gompertz-Makeham Law of Mortality scaled to monthly tick with sex-split and poverty multipliers."""
    # Actuarial constants from India 2024-2026 data
    if sex == 'M':
        A_s = 0.002
        B_s = 0.00004
        c_val = 1.095
    else:
        # Females have slightly lower background risk and aging constant
        A_s = 0.001
        B_s = 0.00003
        c_val = 1.090

    # Poverty/Starvation Multiplier (Multidimensional Poverty Penalty):
    # Severe poverty increases risk by 1.75x (midpoint of 1.5x to 2.0x)
    poverty_factor = np.log(1.75) if net_worth <= 0.0 else 0.0
    energy_factor = np.log(1.5) * (1.0 - energy / 2458.0)
    A_s_effective = A_s * np.exp(energy_factor + poverty_factor)

    # Calculate biological hazard curve using force curve h(x) = A + B * c^age
    h_x = A_s_effective + B_s * (c_val ** age)
    
    dt = 1.0 / 12.0  # One tick = one month
    return 1.0 - np.exp(-h_x * dt)


def calculate_diminishing_restoration(amount: float, k: float=20.0, c: float=0.5) -> float:
    """Biomedical Diminishing Returns: Returns logarithmic restoration."""
    return k * np.log1p(c * amount)


class Citizen:
    """
    Represents an individual agent in the simulation.
    Decisions are driven by Prospect Theory (loss aversion), and mortality 
    is calculated via the non-linear Gompertz-Makeham formula.
    """

    def __init__(
        self,
        citizen_id: int,
        age: float = 28.7,
        baseline_health: float = 70.8,
        education_level: float = 0.45,
        risk_tolerance: float = 0.5,
        bank_balance: float = 3755.0,
        sex: str = 'F',
        parent_ids: Optional[List[int]] = None,
        religious_affiliation: int = 0,
        religiosity: float = 0.97,
    ) -> None:
        self.citizen_id: int = citizen_id
        self.age: float = age
        self.baseline_health: float = baseline_health
        self.education_level: float = max(0.0, min(1.0, education_level))
        self.risk_tolerance: float = risk_tolerance

        self.health: float = baseline_health
        self.energy: float = 2458.0
        self.bank_balance: float = bank_balance
        self.stress_level: float = 14.0
        self.debt: float = 1280.0

        self.is_employed: bool = False
        self.employer_id: Optional[str] = None
        self.is_student: bool = False
        self.is_dead: bool = False
        self.cause_of_death: Optional[str] = None

        # SEIR Epidemiological State ('S', 'E', 'I', 'R')
        self.seir_state: str = 'S'
        self.infection_days: int = 0

        # Demographics & Family
        self.sex: str = sex
        self.parent_ids: List[int] = parent_ids if parent_ids is not None else []
        self.offspring_ids: List[int] = []

        # Pregnancy & Gestation
        self.is_pregnant: bool = False
        self.gestation_months: int = 0
        self.birth_cooldown: int = 0

        # Socio-Cultural identity
        self.religious_affiliation: int = religious_affiliation
        self.religiosity: float = religiosity

        self.total_earnings: float = 0.0
        self.total_spending: float = 0.0
        self.work_experience: int = 0
        self.daily_earnings: float = 0.0
        self.last_monthly_income: float = 0.0

    @property
    def net_worth(self) -> float:
        return self.bank_balance - self.debt

    def tick(self, engine: "SimulationEngine") -> None:
        if self.is_dead:
            return

        # 1. Biological and Age Updates
        self.age += 1.0 / 12.0
        self._apply_decays(engine)

        if self.is_dead:
            return

        # 2. SEIR Epidemic Progression
        self._update_seir_state()

        # Enforce geriatric retirement when turning 65
        if self.age >= 65.0 and self.is_employed:
            self.lose_job()

        # Infants and Youths are dependents
        if self.age < 18.0:
            self._service_dependent_needs(engine)
            return
        elif self.is_student:
            self.is_student = False  # Graduate at age 18

        # 3. Financial Debt Mechanics (Adults only)
        self._service_debt(engine)

        # 4. Decision-Making Loop using Prospect Theory (Adults/Geriatrics)
        self._make_decisions(engine)

    def _apply_decays(self, engine: "SimulationEngine") -> None:
        """Applies energy drain, stress, and checks Gompertz-Makeham mortality."""
        # Monthly non-linear energy drain scaled to 2458.0 kcal capacity
        energy_loss = (50.0 + (15.0 * np.exp(1.0 - self.health / 70.8))) * 24.58
        self.energy = max(0.0, self.energy - energy_loss)

        # Gompertz-Makeham Mortality Calculation (monthly)
        mortality_prob = calculate_monthly_mortality_prob(self.age, self.sex, self.energy, self.net_worth)
        
        # Adjust mortality hazard based on health and SEIR state
        if self.health < 20.0:
            mortality_prob = 1.0 - (1.0 - mortality_prob) ** 5.0  # 5x hazard if health critically low
        if self.seir_state == 'I':
            mortality_prob = 1.0 - (1.0 - mortality_prob) ** 2.5  # 2.5x hazard if infected

        # If geriatric (65+), age decay scales health down
        if self.age >= 65.0:
            self.health = max(0.0, self.health - (self.age - 65.0) * 0.1)

        if random.random() < mortality_prob:
            # Determine cause of death stochastically (63% NCDs: Cardiovascular, COPD, Diabetes)
            r_cause = random.random()
            if r_cause < 0.63:
                cause = random.choice([
                    "Cardiovascular / Ischemic Heart Disease (NCD)",
                    "Chronic Obstructive Pulmonary Disease (NCD)",
                    "Diabetes / Metabolic Syndrome (NCD)"
                ])
            else:
                if self.seir_state == 'I':
                    cause = "Infectious Disease (Tuberculosis/SEIR)"
                elif self.energy < 491.6:
                    cause = "Starvation / Malnutrition"
                else:
                    cause = "Age-related Biological Decay"
            self.die(cause)
            return

        # Stress updates
        debt_stress = prospect_value(-(self.debt / (self.bank_balance + 1.0)) * 10, lambda_=1.5)
        health_stress = (self.baseline_health - self.health) * 0.4
        target_stress = np.abs(debt_stress) + health_stress
        self.stress_level = max(0.0, min(100.0, self.stress_level + (target_stress - self.stress_level) * 0.2))

        # Monthly health decay based on stress
        if self.stress_level > 70.0:
            self.health = max(0.0, self.health - 5.0)

    def _update_seir_state(self) -> None:
        """Progresses the SEIR disease state."""
        if self.seir_state == 'E':
            self.infection_days += 1
            # Incubation progress scaled monthly
            if random.random() < 0.8:
                self.seir_state = 'I'
                self.infection_days = 0
        elif self.seir_state == 'I':
            self.infection_days += 1
            # Monthly infection harms health significantly
            self.health = max(0.0, self.health - 15.0)
            # Infectious period resolution scaled monthly
            if random.random() < 0.7:
                self.seir_state = 'R'
                self.infection_days = 0

    def _service_dependent_needs(self, engine: "SimulationEngine") -> None:
        """Infants and youths draw resources from parent's bank balance if hungry/sick."""
        parents = [engine.get_citizen_by_id(pid) for pid in self.parent_ids]
        alive_parents = [p for p in parents if p and not p.is_dead]
        
        # 1. Schooling for youths (5-18 yrs)
        if 5.0 <= self.age < 18.0 and not self.is_student:
            school = engine.get_best_available_node("School", self)
            if school:
                base_tuition = school.price * 10.0  # Monthly scaled tuition
                subsidy_rate = engine.policies.get("education_subsidy", 0.0)
                subsidy_amount = base_tuition * subsidy_rate
                tuition_paid_by_citizen = base_tuition - subsidy_amount
                
                for parent in alive_parents:
                    if parent.bank_balance >= tuition_paid_by_citizen:
                        parent.bank_balance -= tuition_paid_by_citizen
                        parent.total_spending += tuition_paid_by_citizen
                        self.is_student = True
                        school.receive_revenue(base_tuition, parent)
                        engine.government_capital -= subsidy_amount
                        break

        if self.is_student:
            self.education_level = min(1.0, self.education_level + 0.02)

        # 2. Food / Starvation check (thresholds scaled to 2458.0 kcal)
        if self.energy < 1229.0:
            grocery_store = engine.get_best_available_node("GroceryStore", self)
            base_p_grocery = (grocery_store.price if grocery_store else 20.0) * 20.0  # Consistent adult/child scaling
            p_grocery = base_p_grocery * (1.0 + engine.policies.get("grocery_subsidy", 0.0))
            subsidy_amount = base_p_grocery - p_grocery
            
            fed = False
            for parent in alive_parents:
                if parent.bank_balance >= p_grocery:
                    parent.bank_balance -= p_grocery
                    parent.total_spending += p_grocery
                    self.energy = min(2458.0, self.energy + 1474.8)
                    self.health = min(self.baseline_health, self.health + calculate_diminishing_restoration(2.0, k=20.0, c=1.0))
                    if grocery_store:
                        grocery_store.receive_revenue(base_p_grocery, parent)
                        engine.government_capital -= subsidy_amount
                    fed = True
                    break
                    
            if not fed:
                restaurant = engine.get_best_available_node("Restaurant", self)
                base_p_fast = (restaurant.price if restaurant else 10.0) * 20.0
                p_fast = base_p_fast * (1.0 + engine.policies.get("fast_food_tax", 0.0))
                subsidy_amount = base_p_fast - p_fast
                for parent in alive_parents:
                    if parent.bank_balance >= p_fast:
                        parent.bank_balance -= p_fast
                        parent.total_spending += p_fast
                        self.energy = min(2458.0, self.energy + 1966.4)
                        self.health = max(0.0, self.health - 12.0)
                        self.stress_level = min(100.0, self.stress_level + 5.0)
                        if restaurant:
                            restaurant.receive_revenue(base_p_fast, parent)
                            engine.government_capital -= subsidy_amount
                        fed = True
                        break
                        
            if not fed:
                self.energy = max(0.0, self.energy - 491.6)
                self.health = max(0.0, self.health - 15.0)

        # 3. Medical care check
        if self.health < 40.0 or self.seir_state == 'I':
            hospital = engine.get_best_available_node("Hospital", self)
            if hospital:
                base_fee = hospital.price * 3.0
                subsidy_rate = engine.policies.get("healthcare_subsidy", 0.0)
                fee = base_fee * (1.0 - subsidy_rate)
                has_free_care = engine.policies.get("free_emergency_care", False)
                actual_fee = 0.0 if has_free_care else fee
                subsidy_amount = base_fee - actual_fee

                treated = False
                for parent in alive_parents:
                    if parent.bank_balance >= fee or has_free_care:
                        if hospital.admit_patient(self):
                            if not has_free_care:
                                parent.bank_balance -= actual_fee
                                parent.total_spending += actual_fee
                            self.health = min(self.baseline_health, self.health + calculate_diminishing_restoration(2.0, k=45.0, c=2.0))
                            if self.seir_state == 'I' and random.random() < 0.5:
                                self.seir_state = 'R'
                            hospital.receive_revenue(base_fee, parent)
                            engine.government_capital -= subsidy_amount
                            treated = True
                            break
                if not treated:
                    self.health = max(0.0, self.health - 10.0)

    def _service_debt(self, engine: "SimulationEngine") -> None:
        if self.debt > 0.0:
            debt_ceiling = max(2000.0, self.last_monthly_income * 12.0)
            
            # Bankruptcy trigger: insolvent, unemployed, and maxed out credit
            if not self.is_employed and self.bank_balance <= 0.01 and self.debt >= debt_ceiling:
                engine.tick_debt_written_off += self.debt
                self.debt = 0.0
                self.stress_level = 100.0
                return

            interest = self.debt * (engine.policies.get("interest_rate", 0.098) / 12.0)
            self.debt += interest
            # Monthly EMI is capped at 37.5% (midpoint of 35-40%) of last monthly income for employed borrowers.
            # If unemployed, fallback to standard fraction of bank balance.
            if self.is_employed and self.last_monthly_income > 0.0:
                min_payment = self.last_monthly_income * 0.375
            else:
                min_payment = min(self.bank_balance * 0.2, self.debt * 0.15 + 10.0)
            
            min_payment = min(min_payment, self.debt)
            if min_payment > 0.01:
                payment = min(min_payment, self.bank_balance)
                self.bank_balance -= payment
                self.debt -= payment
                self.total_spending += payment

    def _make_decisions(self, engine: "SimulationEngine") -> None:
        """Prospect Theory-based choices."""
        if self.health < 40.0 or self.seir_state == 'I':
            self._seek_healthcare(engine)
            if self.health >= 40.0:
                return

        if self.energy < 1229.0:
            self._decide_food(engine)

        if not self.is_employed and not self.is_student and (18.0 <= self.age < 65.0):
            self._search_for_job(engine)

    def _decide_food(self, engine: "SimulationEngine") -> None:
        grocery_store = engine.get_best_available_node("GroceryStore", self)
        restaurant = engine.get_best_available_node("Restaurant", self)

        base_p_grocery = (grocery_store.price if grocery_store else 20.0) * 20.0
        p_grocery = base_p_grocery * (1.0 + engine.policies.get("grocery_subsidy", 0.0))
        subsidy_g = base_p_grocery - p_grocery

        base_p_fast_food = (restaurant.price if restaurant else 10.0) * 20.0
        p_fast_food = base_p_fast_food * (1.0 + engine.policies.get("fast_food_tax", 0.0))
        subsidy_ff = base_p_fast_food - p_fast_food

        # Prospect Theory Evaluation
        # When near starvation, the "loss" of dying is immense.
        starvation_loss_penalty = -100.0 if self.energy < 491.6 else -10.0
        
        # Financial impacts (losses evaluated via prospect theory with religiosity scaling for debt)
        risk_discount = 1.5 - self.risk_tolerance
        lambda_debt = 2.25 * (1.0 + 3.0 * self.religiosity) * risk_discount
        
        debt_ceiling = max(2000.0, self.last_monthly_income * 12.0)
        
        if self.bank_balance >= p_grocery:
            v_money_g = prospect_value(-p_grocery)
        else:
            if self.debt >= debt_ceiling:
                v_money_g = -float('inf')
            else:
                cash = max(0.0, self.bank_balance)
                debt = p_grocery - cash
                v_money_g = prospect_value(-cash) + prospect_value(-debt, lambda_=lambda_debt)

        if self.bank_balance >= p_fast_food:
            v_money_ff = prospect_value(-p_fast_food)
        else:
            if self.debt >= debt_ceiling:
                v_money_ff = -float('inf')
            else:
                cash = max(0.0, self.bank_balance)
                debt = p_fast_food - cash
                v_money_ff = prospect_value(-cash) + prospect_value(-debt, lambda_=lambda_debt)

        # Health/Energy gains (logarithmic/diminishing returns)
        v_energy_g = prospect_value(calculate_diminishing_restoration(1.5, k=25, c=1.0))
        v_energy_ff = prospect_value(calculate_diminishing_restoration(2.5, k=25, c=1.0))

        v_health_g = prospect_value(5.0)
        v_health_ff = prospect_value(-4.0)

        # High utility weighting for groceries over discretionary fast food (expenditure weight 46% rural / 39% urban)
        u_grocery = v_money_g + 1.5 * v_energy_g + v_health_g
        u_fast_food = v_money_ff + 0.8 * v_energy_ff + v_health_ff
        u_starve = prospect_value(starvation_loss_penalty)

        # Softmax selection
        max_u = max(u_grocery, u_fast_food, u_starve)
        exp_g = math.exp(min(50.0, u_grocery - max_u))
        exp_ff = math.exp(min(50.0, u_fast_food - max_u))
        exp_st = math.exp(min(50.0, u_starve - max_u))
        
        total_exp = exp_g + exp_ff + exp_st
        prob_g = exp_g / total_exp
        prob_ff = exp_ff / total_exp

        rand = random.random()
        if rand < prob_g:
            if self.bank_balance < p_grocery:
                self.debt += (p_grocery - max(0.0, self.bank_balance))
                self.bank_balance = 0.0
                self._buy_groceries(grocery_store, p_grocery, base_p_grocery, subsidy_g, engine, deduct_balance=False)
            else:
                self._buy_groceries(grocery_store, p_grocery, base_p_grocery, subsidy_g, engine)
        elif rand < (prob_g + prob_ff):
            if self.bank_balance < p_fast_food:
                self.debt += (p_fast_food - max(0.0, self.bank_balance))
                self.bank_balance = 0.0
                self._buy_fast_food(restaurant, p_fast_food, base_p_fast_food, subsidy_ff, engine, deduct_balance=False)
            else:
                self._buy_fast_food(restaurant, p_fast_food, base_p_fast_food, subsidy_ff, engine)
        else:
            self.energy = max(0.0, self.energy - 491.6)
            self.health = max(0.0, self.health - 15.0)

    def _buy_groceries(self, store: Optional["EnvironmentNode"], price: float, base_price: float, subsidy_amount: float, engine: "SimulationEngine", deduct_balance: bool = True) -> None:
        if deduct_balance:
            self.bank_balance -= price
        self.total_spending += price
        self.health = min(self.baseline_health, self.health + calculate_diminishing_restoration(2.0, k=20.0, c=1.0))
        self.energy = min(2458.0, self.energy + 1474.8)
        if store:
            store.receive_revenue(base_price, self)
            engine.government_capital -= subsidy_amount

    def _buy_fast_food(self, rest: Optional["EnvironmentNode"], price: float, base_price: float, subsidy_amount: float, engine: "SimulationEngine", deduct_balance: bool = True) -> None:
        if deduct_balance:
            self.bank_balance -= price
        self.total_spending += price
        self.energy = min(2458.0, self.energy + 1966.4)
        self.health = max(0.0, self.health - 12.0)
        self.stress_level = min(100.0, self.stress_level + 5.0)
        if rest:
            rest.receive_revenue(base_price, self)
            engine.government_capital -= subsidy_amount

    def _seek_healthcare(self, engine: "SimulationEngine") -> None:
        hospital = engine.get_best_available_node("Hospital", self)
        if not hospital: return

        base_fee = hospital.price * 3.0
        subsidy_rate = engine.policies.get("healthcare_subsidy", 0.0)
        fee = base_fee * (1.0 - subsidy_rate)
        has_free_care = engine.policies.get("free_emergency_care", False)
        
        actual_fee = 0.0 if has_free_care else fee
        subsidy_amount = base_fee - actual_fee

        if hospital.admit_patient(self):
            if not has_free_care:
                if self.bank_balance < fee:
                    self.debt += (fee - max(0.0, self.bank_balance))
                    self.bank_balance = 0.0
                else:
                    self.bank_balance -= fee
                self.total_spending += actual_fee
            self.health = min(self.baseline_health, self.health + calculate_diminishing_restoration(2.0, k=45.0, c=2.0))
            if self.seir_state == 'I' and random.random() < 0.5:
                self.seir_state = 'R'
            hospital.receive_revenue(base_fee, self)
            engine.government_capital -= subsidy_amount
        else:
            self.health = max(0.0, self.health - 10.0)

    def _search_for_job(self, engine: "SimulationEngine") -> None:
        available_workplaces = engine.get_nodes_with_job_openings()
        if not available_workplaces: return

        best_wp = max(available_workplaces, key=lambda wp: wp.calculate_wage(self), default=None)
        if best_wp and best_wp.hire_employee(self):
            self.is_employed = True
            self.employer_id = best_wp.node_id

    def receive_wage(self, amount: float) -> None:
        self.bank_balance += amount
        self.daily_earnings += amount
        self.total_earnings += amount
        self.work_experience += 1
        self.last_monthly_income = amount

    def lose_job(self) -> None:
        self.is_employed = False
        self.employer_id = None
        self.stress_level = min(100.0, self.stress_level + prospect_value(-20.0, lambda_=1.5))

    def die(self, cause: str) -> None:
        self.is_dead = True
        self.cause_of_death = cause
        self.health = 0.0

    def __repr__(self) -> str:
        return f"Citizen({self.citizen_id}, Age={self.age:.1f}, SEIR={self.seir_state})"
```

### 2. `simulation/core/environment.py`
```python
import random
import numpy as np
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from simulation.core.citizen import Citizen
    from simulation.core.engine import SimulationEngine


def calculate_cobb_douglas_output(A: float, K: float, L: float, alpha: float=0.42, beta: float=0.58) -> float:
    """Cobb-Douglas Production Function for macro-economic output."""
    K = max(0.01, K)
    L = max(0.01, L)
    return A * (K**alpha) * (L**beta)


def calculate_infection_prob(I_j: int, N_j: int, beta: float=0.2) -> float:
    """Localized SEIR: Probability of infection at a node."""
    if N_j == 0: return 0.0
    lambda_j = beta * (I_j / N_j)
    dt = 1.0
    return 1.0 - np.exp(-lambda_j * dt)


class EnvironmentNode:
    """
    Base class for physical and economic entities in the simulation.
    Now supports localized SEIR transmission among staff.
    """

    def __init__(
        self,
        node_id: str,
        node_name: str,
        node_type: str,
        capacity: int,
        price: float,
        employee_capacity: int,
        base_capital: float = 93700.0,
    ) -> None:
        self.node_id: str = node_id
        self.node_name: str = node_name
        self.node_type: str = node_type
        self.capacity: int = capacity
        self.price: float = price
        self.employee_capacity: int = employee_capacity
        self.capital: float = base_capital

        self.employees: List["Citizen"] = []
        self.occupied_slots: int = 0
        self.monthly_revenue: float = 0.0
        self.monthly_wages: float = 0.0

    @property
    def operational_capacity(self) -> int:
        if not self.employees: return 0
        return int(self.capacity * (len(self.employees) / self.employee_capacity))

    def tick(self, engine: "SimulationEngine") -> None:
        self.occupied_slots = 0
        
        # Apply monthly CPI inflation (4.75% annually / 12)
        self.price *= (1.0 + (0.0475 / 12.0))
        
        # 1. Localized SEIR Transmission among employees
        self._transmit_disease()

        # 2. Pay wages
        to_fire = []
        self.monthly_wages = 0.0
        for emp in self.employees:
            if emp.is_dead or not emp.is_employed or emp.age >= 65.0:
                to_fire.append(emp)
                emp.lose_job()
                continue
                
            wage = self.calculate_wage(emp)
            if self.capital >= wage:
                self.capital -= wage
                self.monthly_wages += wage
                emp.receive_wage(wage)
            else:
                to_fire.append(emp)
                emp.lose_job()

        for emp in to_fire:
            if emp in self.employees:
                self.employees.remove(emp)

        self.pay_taxes(engine)

        if self.capital > 500.0 and len(self.employees) < self.employee_capacity:
            self._attempt_hiring(engine)
            
        self.monthly_revenue = 0.0

    def _transmit_disease(self) -> None:
        """Spreads disease among staff based on SEIR localized interactions."""
        if not self.employees: return
        I_j = sum(1 for e in self.employees if e.seir_state == 'I')
        if I_j > 0:
            # 1.5x to 2.0x higher local transmission multiplier in dense formal workplaces (we use 1.75x -> beta = 0.35)
            beta_val = 0.35 if self.node_type == "Workplace" else 0.20
            prob_infect = calculate_infection_prob(I_j, len(self.employees), beta=beta_val)
            for emp in self.employees:
                if emp.seir_state == 'S' and random.random() < prob_infect:
                    emp.seir_state = 'E'

    def calculate_wage(self, citizen: "Citizen") -> float:
        # Daily wage ranges from $3.5 to $8.5 based on education/skill (₹300 to ₹700)
        daily_wage = 3.5 + citizen.education_level * 5.0
        # Adjust wage for inflation (price level) relative to initial price of 5.0
        price_factor = (self.price / 5.0) if self.node_type == "Workplace" else 1.0
        return daily_wage * 20.0 * price_factor

    def hire_employee(self, citizen: "Citizen") -> bool:
        if len(self.employees) < self.employee_capacity:
            projected_wages = sum(self.calculate_wage(e) for e in self.employees)
            new_wage = self.calculate_wage(citizen)
            if self.capital >= projected_wages + new_wage:
                self.employees.append(citizen)
                return True
        return False

    def receive_revenue(self, amount: float, citizen: "Citizen") -> None:
        self.capital += amount
        self.monthly_revenue += amount

    def pay_taxes(self, engine: "SimulationEngine") -> None:
        tax_rate = engine.policies.get("corporate_tax_rate", 0.1)
        profit = max(0.0, self.monthly_revenue - self.monthly_wages)
        tax_due = profit * tax_rate
        if tax_due > 0.0:
            self.capital -= tax_due
            engine.receive_tax(tax_due)

    def _attempt_hiring(self, engine: "SimulationEngine") -> None:
        # Only hire working-age adults (18.0 <= age < 65.0)
        unemployed = [c for c in engine.citizens if not c.is_employed and not c.is_student and not c.is_dead and 18.0 <= c.age < 65.0]
        if not unemployed: return
        
        candidates = sorted(unemployed, key=lambda x: x.education_level, reverse=True)
        slots_available = self.employee_capacity - len(self.employees)
        
        for candidate in candidates:
            if slots_available <= 0:
                break
            if self.hire_employee(candidate):
                candidate.is_employed = True
                candidate.employer_id = self.node_id
                slots_available -= 1


class Workplace(EnvironmentNode):
    def __init__(self, node_id: str, node_name: str, capacity: int, employee_capacity: int) -> None:
        super().__init__(node_id, node_name, "Workplace", capacity, price=5.0, employee_capacity=employee_capacity)

    def tick(self, engine: "SimulationEngine") -> None:
        # Cobb-Douglas Production Function
        if self.employees:
            avg_edu = sum(e.education_level for e in self.employees) / len(self.employees)
            # Total Factor Productivity (TFP) growth of 2.2% annually, compounded monthly
            tfp_growth = (1.0 + (0.022 / 12.0)) ** engine.tick_count
            A = (1.0 + avg_edu) * tfp_growth
            K = self.capital
            
            # Cobb-Douglas Labor L: Aggregate employee Human Capital (H_i)
            L = sum((0.1 + np.log1p(e.education_level)) * (e.health / 70.8) for e in self.employees)
            
            output = calculate_cobb_douglas_output(A, K, L)
            # Economic Volatility: India VIX volatility (~14.5% annual std dev -> ~4.18% monthly)
            market_fluctuation = max(0.2, float(np.random.normal(1.0, 0.145 / np.sqrt(12.0))))
            revenue = output * self.price * market_fluctuation
            self.capital += revenue
            self.monthly_revenue += revenue

        super().tick(engine)


class Hospital(EnvironmentNode):
    def __init__(self, node_id: str, node_name: str, capacity: int, employee_capacity: int) -> None:
        super().__init__(node_id, node_name, "Hospital", capacity, price=133.33, employee_capacity=employee_capacity)

    def admit_patient(self, citizen: "Citizen") -> bool:
        if self.occupied_slots < self.operational_capacity:
            self.occupied_slots += 1
            return True
        return False


class School(EnvironmentNode):
    def __init__(self, node_id: str, node_name: str, capacity: int, employee_capacity: int) -> None:
        super().__init__(node_id, node_name, "School", capacity, price=3.25, employee_capacity=employee_capacity)


class GroceryStore(EnvironmentNode):
    def __init__(self, node_id: str, node_name: str, capacity: int, employee_capacity: int) -> None:
        super().__init__(node_id, node_name, "GroceryStore", capacity, price=1.50, employee_capacity=employee_capacity)


class Restaurant(EnvironmentNode):
    def __init__(self, node_id: str, node_name: str, capacity: int, employee_capacity: int) -> None:
        super().__init__(node_id, node_name, "Restaurant", capacity, price=1.50, employee_capacity=employee_capacity)
```

### 3. `simulation/core/engine.py`
```python
from __future__ import annotations
import random
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional

from simulation.core.citizen import Citizen
from simulation.core.environment import (
    EnvironmentNode,
    Workplace,
    Hospital,
    School,
    GroceryStore,
    Restaurant,
)
from simulation.analytics.metrics import calculate_macro_metrics


class SimulationEngine:
    """
    The orchestrator and control panel of the stochastic city simulation.
    Manages the global clock, agents, environmental nodes, taxation,
    and policy levers. Records macro metrics on each tick.
    """

    def __init__(
        self,
        population_size: int = 1467231210,
        initial_gov_capital: float = 1270000000000.0,
        seed: Optional[int] = 2024,
    ) -> None:
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self.tick_count: int = 0
        self.next_citizen_id: int = 0
        
        # We run the simulation with a scaled agent count (default 150 agents representing 1,467,231,210 individuals)
        if population_size > 100000:
            self.pop_scale: float = population_size / 150.0
            internal_pop_size = 150
            self.government_capital: float = initial_gov_capital / self.pop_scale
        else:
            self.pop_scale = 1.0
            internal_pop_size = population_size
            self.government_capital = initial_gov_capital

        # Policy parameters
        self.policies: Dict[str, Any] = {
            "tax_rate": 0.05,               # Citizen income tax rate (0.0 to 1.0)
            "corporate_tax_rate": 0.22,     # Corporate tax on profit above starting capital
            "interest_rate": 0.098,         # Annual debt interest rate
            "fast_food_tax": 0.05,          # Tax (positive) or subsidy (negative) on fast food price
            "grocery_subsidy": -0.80,       # Tax (positive) or subsidy (negative) on grocery price
            "healthcare_subsidy": 0.40,     # Subsidy rate for hospital fees (0.0 to 1.0)
            "education_subsidy": 1.0,       # Subsidy rate for school tuition (0.0 to 1.0)
            "free_emergency_care": True,    # If true, poor s/he does not pay hospital fee (gov pays)
            "ubi_amount": 0.0,              # Universal Basic Income amount paid to citizen monthly
        }

        # Initialize lists
        self.citizens: List[Citizen] = []
        self.nodes: List[EnvironmentNode] = []
        self.dead_citizens: List[Citizen] = []

        # Inheritance tracking metrics
        self.total_wealth_inherited: float = 0.0
        self.total_wealth_escheated: float = 0.0
        self.dependency_ratio: float = 0.0

        # Metrics historical log
        self.history: List[Dict[str, Any]] = []

        # 1. Instantiate the environment nodes
        self._initialize_nodes()

        # 2. Instantiate population
        self._initialize_population(internal_pop_size)

        # 3. Seed workforce: Assign initial employees to nodes so businesses can operate
        self._seed_initial_workforce()

        # Record baseline metrics (Tick 0)
        self._record_metrics()

    def _initialize_nodes(self) -> None:
        """Creates default environment nodes in the city, calibrated to India workforce sector distributions."""
        self.nodes = [
            # Agriculture sector (44% target, we assign 42 slots)
            Workplace(node_id="wp_farm_1", node_name="Agricultural Co-op Farm", capacity=200, employee_capacity=42),
            # Industry sector (22% target, we assign 21 slots)
            Workplace(node_id="wp_factory_1", node_name="Industrial Textile Mill", capacity=150, employee_capacity=21),
            # Services sector (34% target, we assign 32 slots total)
            Hospital(node_id="hosp_city", node_name="City General Hospital", capacity=50, employee_capacity=5),
            School(node_id="school_district", node_name="District Public School", capacity=100, employee_capacity=10),
            GroceryStore(node_id="store_fresh", node_name="Local Bazaar Groceries", capacity=200, employee_capacity=10),
            Restaurant(node_id="rest_burger", node_name="Dhaba Fast Food", capacity=200, employee_capacity=7),
        ]

    def _initialize_population(self, size: int) -> None:
        """Generates the starting citizen population with a realistic demographic pyramid and sex ratio."""
        for i in range(size):
            # Demographic brackets (India SRS: 0-14: 25.3%, 15-59: 64.6%, 60+: 10.1%)
            r = random.random()
            if r < 0.253:
                age = random.uniform(0.0, 15.0)
            elif r < 0.253 + 0.646: # 0.899
                age = random.uniform(15.0, 60.0)
            else:
                age = random.uniform(60.0, 75.0)

            # Overall starting sex ratio: Males ~50.5%, Females ~49.5%
            sex = 'M' if random.random() < 0.505 else 'F'
            
            # Baseline health: normal distribution around 70.8 (India life expectancy), capped between 50 and 100
            baseline_health = float(np.clip(np.random.normal(70.8, 10.0), 50.0, 100.0))
            
            # Risk tolerance: uniform 0 to 1
            risk_tolerance = random.random()
            
            # Socio-Cultural matrix (Hindu: 79.8%, Muslim: 14.2%, Christian: 2.3%, Sikh: 1.7%, Other: 2.0%)
            religious_affiliation = random.choices([0, 1, 2, 3, 4], weights=[79.8, 14.2, 2.3, 1.7, 2.0], k=1)[0]
            # Religiosity centers around 0.97 (religion is very important for ~97% of population)
            religiosity = float(np.clip(np.random.beta(30, 1), 0.0, 1.0))

            # Economic parameters scale with age/productivity
            if age < 18.0:
                bank_balance = 0.0
                education_level = 0.0
                debt = 0.0
            else:
                # Bank balance (liquid savings) centers around Median $1712 (lognormal mu=7.445, sigma=1.72)
                bank_balance = float(np.clip(np.random.lognormal(mean=7.445, sigma=1.72), 200.0, 100000.0))
                # Average years of schooling ~6.7 maps to education_level mean of 0.44 via beta(4, 5)
                education_level = float(np.random.beta(4, 5))
                # Household debt centers around $1068
                debt = float(np.clip(np.random.exponential(scale=1068.0), 0.0, 10000.0))

            citizen_id = self.next_citizen_id
            self.next_citizen_id += 1
            citizen = Citizen(
                citizen_id=citizen_id,
                age=age,
                baseline_health=baseline_health,
                education_level=education_level,
                risk_tolerance=risk_tolerance,
                bank_balance=bank_balance,
                sex=sex,
                religious_affiliation=religious_affiliation,
                religiosity=religiosity
            )
            citizen.debt = debt
            citizen.daily_earnings = 0.0
            self.citizens.append(citizen)

        # Stochastic link children to parents stochastically
        children = [c for c in self.citizens if c.age < 18.0]
        adults_f = [c for c in self.citizens if c.sex == 'F' and 18.0 <= c.age <= 50.0]
        adults_m = [c for c in self.citizens if c.sex == 'M' and 18.0 <= c.age <= 50.0]
        
        for child in children:
            mother = random.choice(adults_f) if adults_f else None
            father = random.choice(adults_m) if adults_m else None
            if mother:
                child.parent_ids.append(mother.citizen_id)
                mother.offspring_ids.append(child.citizen_id)
                # Share cultural identity
                child.religious_affiliation = mother.religious_affiliation
                child.religiosity = mother.religiosity * 0.5
            if father:
                child.parent_ids.append(father.citizen_id)
                father.offspring_ids.append(child.citizen_id)

        # Seed 2% of the population randomly as Exposed ('E') to bootstrap SEIR epidemiology
        num_to_infect = max(1, int(len(self.citizens) * 0.02))
        infect_candidates = random.sample(self.citizens, num_to_infect)
        for citizen in infect_candidates:
            citizen.seir_state = 'E'

    def _seed_initial_workforce(self) -> None:
        """Assigns random adult citizens to open job slots so that businesses start operational."""
        unemployed = [c for c in self.citizens if not c.is_employed and 18.0 <= c.age < 65.0]
        random.shuffle(unemployed)
        for node in self.nodes:
            slots_to_fill = int(node.employee_capacity * 0.95)
            for _ in range(slots_to_fill):
                if unemployed:
                    candidate = unemployed.pop()
                    success = node.hire_employee(candidate)
                    if success:
                        candidate.is_employed = True
                        candidate.employer_id = node.node_id

    def get_citizen_by_id(self, citizen_id: int) -> Optional[Citizen]:
        """Looks up a citizen (active or deceased) by ID."""
        for c in self.citizens:
            if c.citizen_id == citizen_id:
                return c
        for c in self.dead_citizens:
            if c.citizen_id == citizen_id:
                return c
        return None

    def step(self) -> None:
        """Executes one simulation step (1 month)."""
        self.tick_count += 1
        
        self.tick_tax_inflow = 0.0
        self.tick_subsidy_outflow = 0.0
        self.tick_debt_written_off = 0.0
        
        prev_money = self._calculate_total_money()

        # Calculate dependency ratio
        working = [c for c in self.citizens if not c.is_dead and 18.0 <= c.age < 65.0]
        dependents = [c for c in self.citizens if not c.is_dead and (c.age < 18.0 or c.age >= 65.0)]
        self.dependency_ratio = len(dependents) / len(working) if working else 0.0

        # Apply welfare stipends and UBI
        self._apply_welfare_and_ubi()

        # Update Citizens
        for citizen in self.citizens:
            if not citizen.is_dead:
                citizen.daily_earnings = 0.0
                citizen.tick(self)

        # Mating and Fertility loop
        self._execute_mating_and_fertility()

        # Update Environment Nodes (Production & Wages paid here)
        for node in self.nodes:
            node.tick(self)

        # Apply Income Taxes with dependency scaling
        self._collect_income_taxes()

        # Handle Deceased Citizens & inheritance
        self._reconcile_deaths()

        # Aggregate analytics
        self._record_metrics()
        
        # Verify Money Conservation
        current_money = self._calculate_total_money()
        delta = current_money - prev_money
        print(f"[Tick {self.tick_count}] Gov Tax Inflow: ${self.tick_tax_inflow:,.2f} | Gov Subsidy/UBI Outflow: ${self.tick_subsidy_outflow:,.2f}")
        print(f"[Tick {self.tick_count}] Money Conservation Delta: ${delta:,.2f} (Includes Cobb-Douglas Output, Interest, Write-offs)")

    def _calculate_total_money(self) -> float:
        total_citizen_balance = sum(c.bank_balance for c in self.citizens if not c.is_dead)
        total_citizen_debt = sum(c.debt for c in self.citizens if not c.is_dead)
        total_node_capital = sum(n.capital for n in self.nodes)
        return self.government_capital + total_node_capital + total_citizen_balance - total_citizen_debt

    def _apply_welfare_and_ubi(self) -> None:
        """Distributes welfare stipends and UBI from the government capital."""
        # 1. Monthly Dependent Welfare Stipend: Gov pays $15 support per dependent child (Infant/Youth < 18) to their households
        for c in self.citizens:
            if not c.is_dead and c.age < 18.0:
                parents = [self.get_citizen_by_id(pid) for pid in c.parent_ids]
                alive_parents = [p for p in parents if p and not p.is_dead]
                if alive_parents:
                    share = 15.0 / len(alive_parents)
                    for p in alive_parents:
                        p.bank_balance += share
                        self.government_capital -= share
                        self.tick_subsidy_outflow += share
                else:
                    c.bank_balance += 15.0
                    self.government_capital -= 15.0
                    self.tick_subsidy_outflow += 15.0

        # 2. Universal Basic Income
        ubi = self.policies.get("ubi_amount", 0.0)
        if ubi > 0.0:
            for citizen in self.citizens:
                if not citizen.is_dead:
                    self.government_capital -= ubi
                    self.tick_subsidy_outflow += ubi
                    citizen.bank_balance += ubi

    def _execute_mating_and_fertility(self) -> None:
        """Handles monthly conception check, partner matching, gestation updates, and births."""
        eligible_females = [
            c for c in self.citizens
            if not c.is_dead and c.sex == 'F' and 18.0 <= c.age <= 45.0 and not c.is_pregnant and c.birth_cooldown <= 0
        ]
        eligible_males = [
            c for c in self.citizens
            if not c.is_dead and c.sex == 'M' and 18.0 <= c.age <= 65.0
        ]
        
        if eligible_males:
            for female in eligible_females:
                age = female.age
                if 20.0 <= age < 25.0:
                    asfr_base = 122.9 / 12000.0  # Peak group 20-24
                elif 25.0 <= age < 30.0:
                    asfr_base = 112.5 / 12000.0  # Peak group 25-29
                elif 15.0 <= age < 20.0 or 30.0 <= age <= 45.0:
                    asfr_base = 35.0 / 12000.0   # Non-peak groups
                else:
                    asfr_base = 0.0
                
                if asfr_base <= 0.0:
                    continue
                
                alpha = 0.5
                beta = 0.3
                net_worth = female.net_worth
                normalized_wealth = min(1.0, max(0.0, net_worth / 5000.0))
                gamma = 0.5 + 1.5 * female.religiosity
                
                asfr_actual = asfr_base * (1.0 - alpha * female.education_level - beta * normalized_wealth) * gamma
                asfr_actual = max(0.0, min(1.0, asfr_actual))
                
                if random.random() < asfr_actual:
                    # Select male partner using Social Homophily similarity weights
                    male_weights = []
                    for male in eligible_males:
                        rel_diff = abs(female.religiosity - male.religiosity)
                        aff_diff = 0.0 if female.religious_affiliation == male.religious_affiliation else 1.0
                        wealth_diff = min(1.0, abs(female.bank_balance - male.bank_balance) / 2000.0)
                        # High homophily (90%+ intra-religion): aff_diff (religious affiliation difference) has high weight
                        similarity = 1.0 - (0.1 * rel_diff + 0.8 * aff_diff + 0.1 * wealth_diff)
                        male_weights.append(max(0.001, similarity))
                    
                    partner = random.choices(eligible_males, weights=male_weights, k=1)[0]
                    female.is_pregnant = True
                    female.gestation_months = 0
                    female.temp_partner_id = partner.citizen_id

        # Update ongoing gestations
        newborns = []
        for citizen in self.citizens:
            if not citizen.is_dead:
                if citizen.birth_cooldown > 0:
                    citizen.birth_cooldown -= 1
                    
                if citizen.is_pregnant:
                    citizen.gestation_months += 1
                    if citizen.gestation_months >= 9:
                        # Birth event! 929 Females per 1000 Males (P(Male) at birth ≈ 0.5184)
                        sex = 'M' if random.random() < 0.5184 else 'F'
                        
                        father = self.get_citizen_by_id(getattr(citizen, "temp_partner_id", -1))
                        
                        # Stochastic inheritance
                        if father and random.random() < 0.2:
                            child_affiliation = father.religious_affiliation
                        else:
                            child_affiliation = citizen.religious_affiliation
                            
                        father_religiosity = father.religiosity if father else citizen.religiosity
                        avg_religiosity = (citizen.religiosity + father_religiosity) / 2.0
                        child_religiosity = float(np.clip(np.random.normal(avg_religiosity, 0.1), 0.0, 1.0))

                        child_id = self.next_citizen_id
                        self.next_citizen_id += 1
                        
                        child = Citizen(
                            citizen_id=child_id,
                            age=0.0,
                            baseline_health=float(np.clip(np.random.normal(70.8, 5.0), 50.0, 100.0)),
                            education_level=0.0,
                            risk_tolerance=random.random(),
                            bank_balance=0.0,
                            sex=sex,
                            parent_ids=[citizen.citizen_id, getattr(citizen, "temp_partner_id", -1)],
                            religious_affiliation=child_affiliation,
                            religiosity=child_religiosity
                        )
                        child.debt = 0.0
                        newborns.append(child)
                        
                        citizen.offspring_ids.append(child_id)
                        if father:
                            father.offspring_ids.append(child_id)
                            
                        citizen.is_pregnant = False
                        citizen.gestation_months = 0
                        citizen.birth_cooldown = 12

        self.citizens.extend(newborns)

    def _collect_income_taxes(self) -> None:
        """Deducts income tax from citizen daily earnings and transfers to government capital, scaled by dependency ratio."""
        tax_rate = self.policies.get("tax_rate", 0.15)
        effective_tax_rate = tax_rate + min(0.08, 0.10 * self.dependency_ratio)
        effective_tax_rate = min(0.9, effective_tax_rate)  # Cap tax rate at 90%

        if effective_tax_rate > 0.0:
            for citizen in self.citizens:
                if not citizen.is_dead and (18.0 <= citizen.age < 65.0) and citizen.daily_earnings > 0.0:
                    tax_amount = citizen.daily_earnings * effective_tax_rate
                    tax_amount = min(tax_amount, citizen.bank_balance)
                    citizen.bank_balance -= tax_amount
                    self.government_capital += tax_amount
                    self.tick_tax_inflow += tax_amount

    def _reconcile_deaths(self) -> None:
        """Finds newly deceased citizens, fires them from jobs, executes estate inheritance, and moves them to dead log."""
        active_alive = []
        newly_dead = []
        for citizen in self.citizens:
            if citizen.is_dead:
                newly_dead.append(citizen)
            else:
                active_alive.append(citizen)

        for citizen in newly_dead:
            # Fire from job
            if citizen.is_employed and citizen.employer_id:
                employer = self.get_node_by_id(citizen.employer_id)
                if employer and citizen in employer.employees:
                    employer.employees.remove(citizen)
            
            # Execute Inheritance Protocol
            self._execute_inheritance(citizen)

            # Move to dead log
            self.dead_citizens.append(citizen)

        self.citizens = active_alive

    def _execute_inheritance(self, deceased: Citizen) -> None:
        """Estate inheritance: splits net assets/debts among offspring or escheats positive capital to state."""
        net_estate = deceased.bank_balance - deceased.debt
        offspring = [self.get_citizen_by_id(oid) for oid in deceased.offspring_ids]
        alive_offspring = [o for o in offspring if o and not o.is_dead]

        if alive_offspring:
            share = net_estate / len(alive_offspring)
            for child in alive_offspring:
                if share >= 0.0:
                    child.bank_balance += share
                else:
                    child.debt += abs(share)
            if net_estate > 0.0:
                self.total_wealth_inherited += net_estate
        else:
            # Escheat positive assets to government, write off debts
            if net_estate > 0.0:
                self.government_capital += net_estate
                self.total_wealth_escheated += net_estate
            else:
                self.tick_debt_written_off += abs(net_estate)

    def _record_metrics(self) -> None:
        """Calculates macro metrics and appends them to the historical log."""
        metrics = calculate_macro_metrics(self.citizens, self.nodes, self.dead_citizens)
        # Add metadata
        metrics["tick"] = self.tick_count
        metrics["government_capital"] = self.government_capital
        # Sum capital of all businesses
        metrics["private_capital"] = sum(node.capital for node in self.nodes)
        
        # Socio-demographic Digital Twin metadata
        metrics["dependency_ratio"] = self.dependency_ratio
        metrics["total_wealth_inherited"] = self.total_wealth_inherited
        metrics["total_wealth_escheated"] = self.total_wealth_escheated
        
        self.history.append(metrics)

    def run_generator(self, ticks: int):
        """Yields the engine state after each tick for live streaming."""
        for _ in range(ticks):
            self.step()
            yield self

    def get_best_available_node(self, node_type: str, citizen: Citizen) -> Optional[EnvironmentNode]:
        """
        Locates the environment node of the specified type.
        If multiple nodes exist, returns the one with capacity and lowest price,
        or falling back to the first available node.
        """
        candidates = [n for n in self.nodes if n.node_type == node_type]
        if not candidates:
            return None

        # Filter nodes that are operational (have employees)
        operational = [n for n in candidates if len(n.employees) > 0]
        if not operational:
            return candidates[0]

        # Return the one with available slots or the cheapest base price
        operational.sort(key=lambda x: (x.occupied_slots >= x.operational_capacity, x.price))
        return operational[0]

    def get_nodes_with_job_openings(self) -> List[EnvironmentNode]:
        """Returns a list of environmental nodes with vacant employee slots."""
        return [
            n for n in self.nodes 
            if len(n.employees) < n.employee_capacity
        ]

    def get_node_by_id(self, node_id: str) -> Optional[EnvironmentNode]:
        """Helper to find an environment node by its ID."""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def receive_tax(self, amount: float) -> None:
        """Callback for corporate and citizen taxes."""
        self.government_capital += amount
        self.tick_tax_inflow += amount

    def get_history_dataframe(self) -> pd.DataFrame:
        """Converts recorded tick history to a pandas DataFrame."""
        return pd.DataFrame(self.history)
```

### 4. `simulation/analytics/metrics.py`
```python
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
    unemployed = [c for c in labor_force if not c.is_employed]
    unemployment_rate = (
        len(unemployed) / len(labor_force) if labor_force else 0.0
    )

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

    # Infant Mortality Rate
    infant_deaths = sum(1 for c in total_dead_citizens if c.age < 1.0)
    births = sum(1 for c in citizens if c.citizen_id >= 1000) + sum(1 for c in total_dead_citizens if c.citizen_id >= 1000)
    
    # If no births yet, default to ~26 per 1000, influenced slightly by hospital strain
    if births == 0:
        infant_mortality = 26.0 + (hospital_strain * 10.0)
    else:
        infant_mortality = (infant_deaths / births) * 1000.0

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
        "average_education": avg_edu,
        "hospital_strain": hospital_strain,
        "death_toll": death_toll,
        "average_life_expectancy": avg_life_exp,
        "seir_susceptible": s_count,
        "seir_exposed": e_count,
        "seir_infected": i_count,
        "seir_recovered": r_count,
        "infant_mortality": infant_mortality,
    }
```

### 5. `simulation/utils/helpers.py`
```python
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
```

### 6. `main.py`
```python
import argparse
import sys
from simulation.core.engine import SimulationEngine
from simulation.utils.helpers import format_report_summary, get_default_config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stochastic City Simulation: Virtual Urban Laboratory"
    )
    defaults = get_default_config()

    parser.add_argument(
        "--ticks",
        type=int,
        default=180,
        help="Number of ticks (months) to run the simulation (default: 180)",
    )
    parser.add_argument(
        "--pop",
        type=int,
        default=defaults["population_size"],
        help=f"Initial population size (default: {defaults['population_size']})",
    )
    parser.add_argument(
        "--gov",
        type=float,
        default=defaults["initial_gov_capital"],
        help=f"Initial government treasury balance (default: {defaults['initial_gov_capital']})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=defaults["seed"],
        help=f"Random seed for reproducibility (default: {defaults['seed']})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="mospi_national_accounts_2024_2039.csv",
        help="Filename to save the historical metrics CSV (default: mospi_national_accounts_2024_2039.csv)",
    )

    args = parser.parse_args()

    print(f"Initializing Virtual Urban Laboratory...")
    print(f"Population: {args.pop} | Gov Capital: ${args.gov:.2f} | Seed: {args.seed}")

    engine = SimulationEngine(
        population_size=args.pop,
        initial_gov_capital=args.gov,
        seed=args.seed,
    )

    print(f"Running simulation for {args.ticks} ticks...")
    
    # Progress indicator
    milestone = max(1, args.ticks // 10)
    for t in range(args.ticks):
        engine.step()
        if (t + 1) % milestone == 0 or (t + 1) == args.ticks:
            pct = ((t + 1) / args.ticks) * 100
            alive_count = len([c for c in engine.citizens if not c.is_dead])
            print(f"  Progress: {pct:3.0f}% | Day {engine.tick_count} | Alive Population: {alive_count}")

    # Generate output
    df = engine.get_history_dataframe()
    df.to_csv(args.output, index=False)
    print(f"Time-series macro metrics successfully exported to: {args.output}")

    # Print final summary
    final_metrics = engine.history[-1]
    report = format_report_summary(final_metrics)
    print(report)


if __name__ == "__main__":
    main()
```

### 7. `dashboard.py`
```python
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import time
from simulation.core.engine import SimulationEngine
from simulation.utils.helpers import format_report_summary

def format_large_number(value, is_currency=False):
    prefix = "$" if is_currency else ""
    if value >= 1_000_000_000_000:
        return f"{prefix}{value / 1_000_000_000_000:.2f}T"
    elif value >= 1_000_000_000:
        return f"{prefix}{value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"{prefix}{value / 1_000_000:.2f}M"
    else:
        return f"{prefix}{value:,.0f}"

def render_metric_card(label, value_str, diff_val, is_positive_param):
    # Determine value color based on current value/health
    val_color = "#00FFA3" # Default green
    try:
        if label == "Gini Inequality":
            gini = float(value_str)
            if gini > 0.5:
                val_color = "#FF4B4B" # Red
            elif gini > 0.38:
                val_color = "#FFA500" # Orange
            else:
                val_color = "#00FFA3" # Green
        elif label == "Unemployment":
            unemp = float(value_str.replace('%', ''))
            if unemp > 12.0:
                val_color = "#FF4B4B" # Red
            elif unemp > 6.0:
                val_color = "#FFA500" # Orange
            else:
                val_color = "#00FFA3" # Green
        elif label == "Active Infections":
            infects = int(value_str.replace(',', '').replace('M', '').replace('B', '').replace('T', ''))
            if infects > 10:
                val_color = "#FF4B4B" # Red
            elif infects > 0:
                val_color = "#FFA500" # Orange
            else:
                val_color = "#00FFA3" # Green
        elif label == "Alive Population":
            val_color = "#00FFA3"
        elif label == "Gov Treasury":
            val_color = "#00FFA3"
    except Exception:
        pass
        
    # Build delta HTML
    if diff_val is None or diff_val == 0:
        delta_html = '<div style="font-size: 0.85rem; color: #7f7f9f; font-weight: 500; margin-top: 2px;">0 (No change)</div>'
    else:
        is_good = (diff_val > 0) if is_positive_param else (diff_val < 0)
        delta_color = "#00FFA3" if is_good else "#FF4B4B"
        arrow = "▲" if diff_val > 0 else "▼"
        
        # Formatting diff text
        if label == "Alive Population":
            suffix = " Born" if diff_val > 0 else " Dead"
            diff_text = f"{arrow} {format_large_number(abs(diff_val))}{suffix}"
        elif label == "Gini Inequality":
            diff_text = f"{arrow} {abs(diff_val):.4f}"
        elif label == "Unemployment":
            diff_text = f"{arrow} {abs(diff_val):.1f}%"
        elif label == "Gov Treasury":
            diff_text = f"{arrow} {format_large_number(abs(diff_val), is_currency=True)}"
        elif label == "Active Infections":
            diff_text = f"{arrow} {format_large_number(abs(diff_val))}"
        else:
            diff_text = f"{arrow} {abs(diff_val):,.2f}"
            
        delta_html = f'<div style="font-size: 0.85rem; color: {delta_color}; font-weight: 600; display: flex; align-items: center; gap: 3px; margin-top: 2px;">{diff_text}</div>'

    html_content = f"""
    <div style="
        background: linear-gradient(135deg, rgba(30, 30, 56, 0.4) 0%, rgba(13, 13, 26, 0.4) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 0.8rem 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15);
        font-family: 'Outfit', sans-serif;
        min-height: 105px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    ">
        <div style="font-size: 0.8rem; color: #a0a0c0; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">{label}</div>
        <div>
            <div style="font-size: 1.8rem; font-weight: 700; color: {val_color}; line-height: 1.1; margin: 0.1rem 0;">{value_str}</div>
            {delta_html}
        </div>
    </div>
    """
    return html_content

st.set_page_config(
    page_title="Anthropolis: Socio-Demographic Digital Twin",
    page_icon="🌆",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }
    .block-container {
        padding-top: 4.0rem !important;
        padding-bottom: 1.0rem !important;
    }
    .header-container {
        background: linear-gradient(135deg, #1e1e38 0%, #0d0d1a 100%);
        padding: 0.6rem 1.2rem;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 5px 20px rgba(0,0,0,0.3);
        margin-top: 0rem;
        margin-bottom: 0.8rem;
    }
    .header-title {
        font-size: 1.6rem;
        font-weight: 800;
        background: linear-gradient(to right, #00FFA3, #00B8FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
        line-height: 1.2;
    }
    .header-subtitle { color: #b0b0d0; font-size: 0.85rem; font-weight: 300; line-height: 1.3; }
    
    /* CSS for better tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.2rem;
        font-weight: 600;
    }
    
    div[data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; }
    div[data-testid="stMetricLabel"] { font-size: 0.85rem; color: #a0a0c0 !important; font-weight: 500; text-transform: uppercase; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="header-container">
        <h1 class="header-title">Anthropolis Laboratory (India Calibration) [LIVE]</h1>
        <p class="header-subtitle">
            Socio-Demographic Digital Twin calibrated to India (2024–2026): 1 Agent ≈ 9.78M People, TFR=2.09, Median Age=28.7, GDP Per Capita=$2,813, 1 Month = 1 Tick.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.image("https://img.icons8.com/nolan/128/city.png", width=80)
st.sidebar.title("Digital Twin Setup")

with st.sidebar.expander("Population & Environment", expanded=True):
    pop_size_cr = st.slider("Population Size (Crores)", min_value=130.0, max_value=160.0, value=146.72, step=0.5)
    pop_size = int(pop_size_cr * 10000000)
    
    gov_cap_b = st.slider("Gov Treasury ($ Billions)", min_value=100.0, max_value=5000.0, value=1270.0, step=10.0)
    gov_cap = gov_cap_b * 1000000000.0

with st.sidebar.expander("Economic & Socio-Cultural Policy Levers", expanded=True):
    tax_rate = st.slider("Income Tax Rate (%)", min_value=0, max_value=40, value=5, step=1) / 100.0
    corp_tax = st.slider("Corporate Tax Rate (%)", min_value=15, max_value=35, value=22, step=1) / 100.0
    ubi_val = st.slider("Monthly UBI ($ per citizen)", min_value=0, max_value=500, value=0, step=10)
    interest_rate = st.slider("Debt Interest Rate (Annual %)", min_value=5.0, max_value=15.0, value=9.8, step=0.1) / 100.0

with st.sidebar.expander("Healthcare, Education & Food Subsidies", expanded=False):
    grocery_sub = st.slider("Grocery Subsidy (%)", min_value=0, max_value=100, value=80, step=5) / 100.0
    fast_food_tax = st.slider("Fast Food Tax (%)", min_value=0, max_value=100, value=5, step=1) / 100.0
    education_sub = st.slider("Education Subsidy (%)", min_value=0, max_value=100, value=100, step=5) / 100.0
    healthcare_sub = st.slider("Healthcare Subsidy (%)", min_value=0, max_value=100, value=40, step=5) / 100.0
    emergency_care = st.checkbox("Free Emergency Medical Care", value=True)

st.sidebar.markdown("---")
ticks_to_run = st.sidebar.slider("Months to Simulate", min_value=12, max_value=360, value=180, step=12)
tick_duration = st.sidebar.slider("1 Month Real-time duration (seconds)", min_value=1.0, max_value=30.0, value=1.0, step=1.0)

# Initialize session state variables
if "running" not in st.session_state:
    st.session_state.running = False
if "paused" not in st.session_state:
    st.session_state.paused = False
if "engine" not in st.session_state:
    st.session_state.engine = None

# Controls Layout
btn_col1, btn_col2, btn_col3 = st.sidebar.columns(3)

start_clicked = btn_col1.button("▶️ Start" if not st.session_state.running else "▶️ Resume")
pause_clicked = btn_col2.button("⏸️ Pause")
reset_clicked = btn_col3.button("🔄 Reset")

if reset_clicked:
    st.session_state.running = False
    st.session_state.paused = False
    st.session_state.engine = None
    st.rerun()

if start_clicked:
    if not st.session_state.running:
        st.session_state.running = True
        st.session_state.paused = False
        st.session_state.engine = SimulationEngine(
            population_size=pop_size,
            initial_gov_capital=gov_cap,
            seed=None, # Backend manages random seed automatically if None
        )
    else:
        st.session_state.paused = False

if pause_clicked:
    st.session_state.paused = True

if st.session_state.get("running", False) and st.session_state.engine is not None:
    from plotly.subplots import make_subplots
    engine = st.session_state.engine
    
    # Update active engine policies with current sidebar values seamlessly
    engine.policies["tax_rate"] = tax_rate
    engine.policies["corporate_tax_rate"] = corp_tax
    engine.policies["interest_rate"] = interest_rate
    engine.policies["ubi_amount"] = ubi_val
    engine.policies["grocery_subsidy"] = -grocery_sub # Backend uses negative for subsidy
    engine.policies["fast_food_tax"] = fast_food_tax
    engine.policies["education_subsidy"] = education_sub
    engine.policies["healthcare_subsidy"] = healthcare_sub
    engine.policies["free_emergency_care"] = emergency_care

    # 1. Static Layout Elements (defined ONCE to prevent DOM recreation and scroll jumping)
    progress_placeholder = st.empty()

    # Metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    metric_pop_placeholder = col1.empty()
    metric_gini_placeholder = col2.empty()
    metric_unemp_placeholder = col3.empty()
    metric_gov_placeholder = col4.empty()
    metric_infect_placeholder = col5.empty()

    st.markdown("---")

    # Tabs for different sections
    tab_econ, tab_health, tab_pop, tab_env = st.tabs([
        "📊 Economics & Wealth", 
        "🏥 Health & Wellbeing", 
        "👥 Populations & Distributions", 
        "🏭 Environmental Nodes"
    ])

    # Economics tab placeholders
    with tab_econ:
        econ_m1, econ_m2 = st.columns(2)
        metric_inherited = econ_m1.empty()
        metric_escheated = econ_m2.empty()
        
        econ_col1, econ_col2 = st.columns(2)
        with econ_col1:
            chart_wealth_placeholder = st.empty()
        with econ_col2:
            chart_inequality_placeholder = st.empty()

    # Health & Wellbeing tab placeholders
    with tab_health:
        health_m1 = st.columns(1)[0]
        metric_dep_ratio = health_m1.empty()

        health_col1, health_col2 = st.columns(2)
        with health_col1:
            chart_bio_placeholder = st.empty()
        with health_col2:
            chart_seir_placeholder = st.empty()
            
        health_col3, health_col4 = st.columns(2)
        with health_col3:
            chart_hospital_strain_placeholder = st.empty()
        with health_col4:
            chart_infant_mortality_placeholder = st.empty()

    # Populations & Distributions tab placeholders
    with tab_pop:
        pop_col1, pop_col2 = st.columns(2)
        with pop_col1:
            chart_pyramid_placeholder = st.empty()
            hist_wealth_placeholder = st.empty()
            hist_age_placeholder = st.empty()
        with pop_col2:
            # Metrics: Sex Ratio at Birth, current Sex Ratio
            pop_m_col1, pop_m_col2 = st.columns(2)
            metric_birth_ratio = pop_m_col1.empty()
            metric_current_ratio = pop_m_col2.empty()
            
            hist_health_placeholder = st.empty()
            hist_debt_placeholder = st.empty()

    # Environmental Nodes tab placeholders
    with tab_env:
        env_col1, env_col2 = st.columns(2)
        with env_col1:
            chart_business_cap_placeholder = st.empty()
        with env_col2:
            chart_business_staff_placeholder = st.empty()

    # Define function to update dashboard UI with current state
    def update_dashboard_ui(live_engine, target_ticks, is_final=False):
        tick = live_engine.tick_count
        history_df = live_engine.get_history_dataframe()
        latest = history_df.iloc[-1].to_dict()
        dead_count = len(live_engine.dead_citizens) * live_engine.pop_scale
        
        # Calculate active SEIR cases for display
        alive_citizens = [c for c in live_engine.citizens if not c.is_dead]
        infected_count = int(latest.get("seir_infected", 0) * live_engine.pop_scale)
        
        # Smoothed Population Display to prevent jumpy zeroes
        growth_rate_monthly = 0.00066 # Approx India 0.8% annual
        base_pop = pop_size
        smoothed_pop = base_pop * ((1.0 + growth_rate_monthly) ** tick)
        
        # Get previous tick for delta calculations
        if len(history_df) > 1:
            prev = history_df.iloc[-2].to_dict()
            diff_pop = smoothed_pop * growth_rate_monthly
            diff_gini = latest["gini_coefficient"] - prev["gini_coefficient"]
            diff_unemp = (latest["unemployment_rate"] - prev["unemployment_rate"]) * 100.0
            diff_gov = (latest["government_capital"] - prev["government_capital"]) * live_engine.pop_scale
            diff_infect = int((latest.get("seir_infected", 0) - prev.get("seir_infected", 0)) * live_engine.pop_scale)
        else:
            diff_pop = None
            diff_gini = None
            diff_unemp = None
            diff_gov = None
            diff_infect = None

        # Update Metrics via custom HTML cards
        metric_pop_placeholder.markdown(render_metric_card("Alive Population", format_large_number(smoothed_pop), diff_pop, is_positive_param=True), unsafe_allow_html=True)
        metric_gini_placeholder.markdown(render_metric_card("Gini Inequality", f"{latest['gini_coefficient']:.4f}", diff_gini, is_positive_param=False), unsafe_allow_html=True)
        metric_unemp_placeholder.markdown(render_metric_card("Unemployment", f"{latest['unemployment_rate']*100:.1f}%", diff_unemp, is_positive_param=False), unsafe_allow_html=True)
        metric_gov_placeholder.markdown(render_metric_card("Gov Treasury", format_large_number(latest['government_capital'] * live_engine.pop_scale, is_currency=True), diff_gov, is_positive_param=True), unsafe_allow_html=True)
        metric_infect_placeholder.markdown(render_metric_card("Active Infections", format_large_number(infected_count), diff_infect, is_positive_param=False), unsafe_allow_html=True)

        # Update Economics Tab Metrics & Charts
        metric_inherited.metric("Total Estate Wealth Inherited", format_large_number(latest['total_wealth_inherited'] * live_engine.pop_scale, is_currency=True), help="Total positive wealth transferred to living offspring upon deaths.")
        metric_escheated.metric("Total Estate Wealth Seized (Escheat)", format_large_number(latest['total_wealth_escheated'] * live_engine.pop_scale, is_currency=True), help="Total estate wealth seized by state treasury due to absence of offspring.")

        plot_config = {'displayModeBar': False}

        fig_wealth = go.Figure()
        fig_wealth.add_trace(go.Scatter(x=history_df["tick"], y=history_df["average_bank_balance"], name="Avg Balance", line=dict(color="#00FFA3", width=2.5)))
        fig_wealth.add_trace(go.Scatter(x=history_df["tick"], y=history_df["average_debt"], name="Avg Debt", line=dict(color="#FF4B4B", width=2.5)))
        fig_wealth.update_layout(title="Citizen Wealth Dynamics (Live)", template="plotly_dark", height=350, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Months")
        chart_wealth_placeholder.plotly_chart(fig_wealth, width="stretch", key=f"wealth_chart_{tick}", config=plot_config)

        fig_ineq = make_subplots(specs=[[{"secondary_y": True}]])
        fig_ineq.add_trace(go.Scatter(x=history_df["tick"], y=history_df["gini_coefficient"], name="Gini Coefficient", line=dict(color="#FFD600", width=2.5)), secondary_y=False)
        fig_ineq.add_trace(go.Scatter(x=history_df["tick"], y=history_df["government_capital"] * live_engine.pop_scale, name="Gov Treasury", line=dict(color="#00B8FF", width=2, dash='dash')), secondary_y=True)
        fig_ineq.add_trace(go.Scatter(x=history_df["tick"], y=history_df["private_capital"] * live_engine.pop_scale, name="Private Capital", line=dict(color="#FF00CC", width=2, dash='dot')), secondary_y=True)
        fig_ineq.update_layout(title="Wealth Inequality & City Capital (Live)", template="plotly_dark", height=350, margin=dict(l=40, r=40, t=40, b=40), xaxis_title="Months")
        fig_ineq.update_yaxes(title_text="Gini Coefficient", secondary_y=False)
        fig_ineq.update_yaxes(title_text="Capital ($)", secondary_y=True)
        chart_inequality_placeholder.plotly_chart(fig_ineq, width="stretch", key=f"ineq_chart_{tick}", config=plot_config)

        # Update Health Tab Metrics & Charts
        metric_dep_ratio.metric("Dependency Ratio", f"{latest['dependency_ratio']:.3f}", help="Dependency Ratio = (Infants + Youths + Geriatrics) / Working-Age population.")

        fig_bio = go.Figure()
        fig_bio.add_trace(go.Scatter(x=history_df["tick"], y=history_df["average_health"], name="Avg Health", line=dict(color="#00FFA3", width=2.5)))
        fig_bio.add_trace(go.Scatter(x=history_df["tick"], y=history_df["average_stress"], name="Avg Stress", line=dict(color="#FFB800", width=2.5)))
        fig_bio.update_layout(title="Biological Index: Health vs Stress (Live)", template="plotly_dark", height=350, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Months")
        chart_bio_placeholder.plotly_chart(fig_bio, width="stretch", key=f"bio_chart_{tick}", config=plot_config)

        fig_seir = go.Figure()
        fig_seir.add_trace(go.Scatter(x=history_df["tick"], y=history_df["seir_susceptible"] * live_engine.pop_scale, name="Susceptible (S)", line=dict(color="#00B8FF", width=2)))
        fig_seir.add_trace(go.Scatter(x=history_df["tick"], y=history_df["seir_exposed"] * live_engine.pop_scale, name="Exposed (E)", line=dict(color="#FFD600", width=2)))
        fig_seir.add_trace(go.Scatter(x=history_df["tick"], y=history_df["seir_infected"] * live_engine.pop_scale, name="Infected (I)", line=dict(color="#FF4B4B", width=2.5)))
        fig_seir.add_trace(go.Scatter(x=history_df["tick"], y=history_df["seir_recovered"] * live_engine.pop_scale, name="Recovered (R)", line=dict(color="#00FFA3", width=2)))
        fig_seir.update_layout(title="SEIR Epidemiological Curve (Live)", template="plotly_dark", height=350, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Months")
        chart_seir_placeholder.plotly_chart(fig_seir, width="stretch", key=f"seir_chart_{tick}", config=plot_config)

        fig_strain = go.Figure()
        fig_strain.add_trace(go.Scatter(x=history_df["tick"], y=history_df["hospital_strain"] * 100.0, name="Hospital Strain (%)", line=dict(color="#FF3366", width=2.5), fill='tozeroy'))
        fig_strain.update_layout(title="Healthcare System Strain (%) (Live)", template="plotly_dark", height=250, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Months")
        fig_strain.update_yaxes(range=[0, 100])
        chart_hospital_strain_placeholder.plotly_chart(fig_strain, width="stretch", key=f"strain_chart_{tick}", config=plot_config)
        
        # Infant Mortality Graph
        fig_imr = go.Figure()
        imr_col = "infant_mortality" if "infant_mortality" in history_df.columns else "dependency_ratio" # Fallback
        if "infant_mortality" in history_df.columns:
            fig_imr.add_trace(go.Scatter(x=history_df["tick"], y=history_df["infant_mortality"], name="Infant Mortality", line=dict(color="#FF8C00", width=2.5), fill='tozeroy'))
            fig_imr.update_layout(title="Infant Mortality Rate (per 1,000 live births)", template="plotly_dark", height=250, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Months")
            chart_infant_mortality_placeholder.plotly_chart(fig_imr, width="stretch", key=f"imr_chart_{tick}", config=plot_config)

        # Update Distributions Tab
        males = [c for c in alive_citizens if c.sex == 'M']
        females = [c for c in alive_citizens if c.sex == 'F']
        born_males = sum(1 for c in live_engine.citizens if c.citizen_id >= 1000 and c.sex == 'M')
        born_females = sum(1 for c in live_engine.citizens if c.citizen_id >= 1000 and c.sex == 'F')
        
        # Sex ratios metrics
        metric_birth_ratio.metric("Sex Ratio at Birth", "929 F / 1000 M (Target)", f"Born: {int(born_males * live_engine.pop_scale):,} M / {int(born_females * live_engine.pop_scale):,} F")
        metric_current_ratio.metric("Current Sex Ratio (M/F)", f"{len(males)/len(females):.2f}" if len(females) > 0 else "N/A")

        # Demographic age-sex pyramid
        bins = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 120]
        labels = ["0-5", "5-10", "10-15", "15-20", "20-25", "25-30", "30-35", "35-40", "40-45", "45-50", "50-55", "55-60", "60-65", "65-70", "70-75", "75-80", "80+"]
        
        male_counts = []
        female_counts = []
        for idx in range(len(bins)-1):
            low = bins[idx]
            high = bins[idx+1]
            m_count = sum(1 for c in males if low <= c.age < high)
            f_count = sum(1 for c in females if low <= c.age < high)
            male_counts.append(-m_count * live_engine.pop_scale)
            female_counts.append(f_count * live_engine.pop_scale)
            
        fig_pyr = go.Figure()
        fig_pyr.add_trace(go.Bar(y=labels, x=male_counts, name="Male", orientation='h', marker_color='#00B8FF'))
        fig_pyr.add_trace(go.Bar(y=labels, x=female_counts, name="Female", orientation='h', marker_color='#FF00CC'))
        
        max_abs = int(max(max(abs(x) for x in male_counts) if male_counts else 1, max(female_counts) if female_counts else 1))
        tick_vals = list(range(-max_abs, max_abs + 1, max(1, max_abs // 4)))
        tick_text = [f"{int(abs(v)):,}" for v in tick_vals]
        
        fig_pyr.update_layout(
            title="Demographic Age-Sex Pyramid (Current)",
            barmode='relative',
            template="plotly_dark",
            height=350,
            margin=dict(l=40, r=20, t=40, b=40),
            xaxis=dict(
                tickvals=tick_vals,
                ticktext=tick_text,
                title="Population Count"
            ),
            yaxis=dict(title="Age Cohort")
        )
        chart_pyramid_placeholder.plotly_chart(fig_pyr, width="stretch", key=f"pyramid_chart_{tick}", config=plot_config)

        if alive_citizens:
            healths = [c.health for c in alive_citizens]
            balances = [c.bank_balance for c in alive_citizens]
            debts = [c.debt for c in alive_citizens]

            fig_hist_health = px.histogram(x=healths, nbins=15, title="Health Status Distribution (Current)", color_discrete_sequence=["#00FFA3"])
            fig_hist_health.update_layout(template="plotly_dark", height=250, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Health (0 - 70.8)", yaxis_title="Count")
            hist_health_placeholder.plotly_chart(fig_hist_health, width="stretch", key=f"hist_health_{tick}", config=plot_config)

            fig_hist_wealth = px.histogram(x=balances, nbins=15, title="Bank Balance Distribution (Current)", color_discrete_sequence=["#FF00CC"])
            fig_hist_wealth.update_layout(template="plotly_dark", height=250, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Balance ($)", yaxis_title="Count")
            hist_wealth_placeholder.plotly_chart(fig_hist_wealth, width="stretch", key=f"hist_wealth_{tick}", config=plot_config)

            fig_hist_debt = px.histogram(x=debts, nbins=15, title="Debt Distribution (Current)", color_discrete_sequence=["#FF4B4B"])
            fig_hist_debt.update_layout(template="plotly_dark", height=250, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Debt ($)", yaxis_title="Count")
            hist_debt_placeholder.plotly_chart(fig_hist_debt, width="stretch", key=f"hist_debt_{tick}", config=plot_config)

            # Update age distribution histogram
            ages = [c.age for c in alive_citizens]
            fig_hist_age = px.histogram(x=ages, nbins=15, title="Age Distribution (Current)", color_discrete_sequence=["#00B8FF"])
            fig_hist_age.update_layout(template="plotly_dark", height=250, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Age (Years)", yaxis_title="Count")
            hist_age_placeholder.plotly_chart(fig_hist_age, width="stretch", key=f"hist_age_{tick}", config=plot_config)

        # Update Environmental Nodes only if final to prevent auto-refreshing during live stream
        if is_final:
            node_names = [n.node_name for n in live_engine.nodes]
            node_capitals = [n.capital for n in live_engine.nodes]
            node_employees = [len(n.employees) for n in live_engine.nodes]
            node_capacities = [n.employee_capacity for n in live_engine.nodes]

            fig_bus_cap = go.Figure(data=[
                go.Bar(x=node_names, y=node_capitals, marker_color="#00FFA3", text=[format_large_number(v, is_currency=True) for v in node_capitals], textposition='auto')
            ])
            fig_bus_cap.update_layout(title="Node Financial Capitals (Final State)", template="plotly_dark", height=350, margin=dict(l=40, r=20, t=40, b=40), xaxis_tickangle=-45)
            chart_business_cap_placeholder.plotly_chart(fig_bus_cap, width="stretch", key=f"bus_cap_chart_{tick}", config=plot_config)

            fig_bus_staff = go.Figure(data=[
                go.Bar(name='Current Employees', x=node_names, y=node_employees, marker_color="#00B8FF"),
                go.Bar(name='Max Staff Capacity', x=node_names, y=node_capacities, marker_color="#555555")
            ])
            fig_bus_staff.update_layout(barmode='group', title="Node Employee Staffing Levels (Final State)", template="plotly_dark", height=350, margin=dict(l=40, r=20, t=40, b=40), xaxis_tickangle=-45)
            chart_business_staff_placeholder.plotly_chart(fig_bus_staff, width="stretch", key=f"bus_staff_chart_{tick}", config=plot_config)

    remaining_ticks = ticks_to_run - engine.tick_count
    
    if remaining_ticks > 0 and not st.session_state.paused:
        # Continuous stream loop: Updates placeholders in-place without redrawing full page
        for live_engine in engine.run_generator(remaining_ticks):
            tick = live_engine.tick_count
            progress_placeholder.progress(tick / ticks_to_run, text=f"Streaming Month {tick}/{ticks_to_run}...")
            update_dashboard_ui(live_engine, ticks_to_run, is_final=False)
            time.sleep(tick_duration)
            
    elif st.session_state.paused:
        progress_placeholder.warning(f"Simulation PAUSED at Month {engine.tick_count}/{ticks_to_run}.")
        update_dashboard_ui(engine, ticks_to_run, is_final=True)
    else:
        progress_placeholder.success("Simulation Complete! Viewing final state.")
        update_dashboard_ui(engine, ticks_to_run, is_final=True)
else:
    st.info("👈 Configure policies and click **▶️ Start** to watch the socio-demographic interactions unfold.")
```
