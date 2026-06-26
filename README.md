# 🌆 Anthropolis: Socio-Demographic Digital Twin

Anthropolis is a modular, stochastic, object-oriented Agent-Based Modeling (ABM) and System Dynamics Digital Twin built in Python. The simulation models a closed-loop urban economy where macro-level economic, demographic, and biological outcomes emerge organically from micro-level socio-cultural traits, family dependencies, and individual citizen decisions.

The current iteration of Anthropolis is strictly calibrated to the real-world demographics and macroeconomics of **India (2024–2026)**. It utilizes an internal scaling engine, allowing a representative subset of agents (e.g. 5,000 agents) to accurately reflect the behaviors and metrics of a 1.46 Billion population.

---

## 🏛️ Simulation Architecture

The Digital Twin operates across three coupled architectural layers:

```text
                  ┌──────────────────────────────────────────┐
                  │          System Dynamics Engine          │
                  │   - Global monthly event orchestration   │
                  │   - Dependency Ratio tax surcharges      │
                  │   - Estate inheritance & UBI payouts     │
                  └────────────────────┬─────────────────────┘
                                       │
                                       ▼
                  ┌──────────────────────────────────────────┐
                  │            Macro-Environment             │
                  │   - Cobb-Douglas production (sum H_i)    │
                  │   - Physical nodes (Hospitals, Schools)  │
                  │   - Workplace SEIR transmission & hires  │
                  └────────────────────┬─────────────────────┘
                                       │
                                       ▼
                  ┌──────────────────────────────────────────┐
                  │             Micro-Citizens               │
                  │   - Sex, Location (Urban/Rural), Caste   │
                  │   - Religiosity & Religious Affiliations │
                  │   - Homophily-based partner matching     │
                  │   - Chain Migration & Dynamic Fertility  │
                  └──────────────────────────────────────────┘
```

### A. The Micro-Layer (Agent Demographics & Choices)
Defined in `simulation/core/citizen.py`.
Each **Citizen** represents an individual with:
- **Demographics**: `sex` (seeded with realistic SRB targets), `age`, `location` (Urban/Rural), `caste` (General/OBC/SC/ST).
- **Migration Networks**: Long-term unemployed rural citizens stochastically migrate to Urban centers, with massive probability spikes if family members have already migrated (simulating Chain Migration).
- **Cohorts**:
  - **Infants** (0-5 yrs) and **Youths** (5-18 yrs): Unproductive dependents who draw food and tuition resources from parent balances. Youths enroll stochastically in school to raise education levels. If parents become bankrupt, youths are stochastically disenrolled.
  - **Working-Age** (18-65 yrs): Core labor supply. Unemployed working-age agents are stochastically absorbed into the **Informal Sector** for self-employment based on education level.
  - **Geriatrics** (65+ yrs): Retired; experience biological age-driven health decay.
- **Socio-Cultural Matrix**:
  - `religious_affiliation`, `religiosity` (0.0 to 1.0), and `risk_tolerance` are inherited stochastically from parents.
  - High religiosity shifts Prospect Theory curves by scaling loss aversion ($\lambda$) for debt, rendering highly religious agents debt-averse.
- **Stochastic Feeding Choices**: Evaluated monthly. Citizens purchase groceries or fast food based on a softmax utility function. If their bank balance is insufficient, they stochastically decide to accumulate debt or starve.

### B. The Macro-Layer (The Environment & Human Capital)
Defined in `simulation/core/environment.py`.
- **Cobb-Douglas Labor Vector ($L$)**: Workplace labor input aggregates employee **Human Capital ($H_i$)**.
  $$L = \sum_{i \in \text{Employees}} H_i \quad \text{where} \quad H_i = \ln(\text{Education}_i + 1) \times \left(\frac{\text{Health}_i}{70.8}\right)$$
- **Wage Stratification**: Baseline wages are calculated based on education and the node's price factor, but are subsequently scaled by multiplying structural discrimination penalties based on `caste` and `religious_affiliation`, perfectly matching real-world systemic inequalities.
- **Open Economy (Trade & Global Capital)**: Workplaces export 20% of output but spend 15% on imported raw materials. Consumers leak 5% of all spending to imported goods, causing capital drains. The economy is counter-balanced by stochastic Foreign Direct Investment (FDI) and direct expatriate remittances injected directly into citizen bank accounts.

### C. The Control Panel (System Dynamics & Taxation)
Defined in `simulation/core/engine.py`.
- **Time Scale**: **1 Tick = 1 Month**. Decays, interest rates, and production rates are scaled monthly.
- **Dependency Ratio Mechanism**: Calculated monthly as:
  $$\text{Dependency Ratio} = \frac{N_{\text{Infant}} + N_{\text{Youth}} + N_{\text{Geriatric}}}{N_{\text{Working}}}$$
  This scales the government's tax surcharge and welfare costs.
- **The Shadow Economy (Informal Sector)**: Absorbed informal workers are counted as employed but have a strict **0% tax compliance rate**. Furthermore, they exhibit strictly partitioned consumption behavior, purchasing goods exclusively from `is_informal` nodes (e.g. Street Vendors) which **do not remit Consumption Tax (GST)** to the government.
- **Consumption Tax (GST Proxy)**: A flat consumption tax applied to formal food and healthcare purchases, remitted by formal selling nodes directly from gross capital to the government.
- **Inheritance Protocol**: Upon a citizen's death, their Net Estate (assets minus debt liabilities) is divided stochastically among living offspring. If no offspring are alive, positive assets are seized by the state treasury via escheatment, and liabilities are written off.
- **Execution Sequencing Safeguards**: The engine enforces strict execution ordering (citizen updates -> business wage payments -> tax collections) verified via run-time assertions to ensure financial and tax integrity.

### D. Performance & Concurrency (Scaling Architecture)
- **Concurrent Map-Reduce Execution**: To overcome single-threaded CPU bottlenecks, the simulation evaluates citizen micro-decisions (Prospect theory, Gompertz mortality, localized SEIR updates) via a `concurrent.futures.ThreadPoolExecutor`. This architecture natively supports multi-core scaling for I/O bounds and C-extensions while ensuring memory consistency.
- **Asymptotic State Optimizations**:
  - Unemployed citizen pools use binary-search $O(\log N)$ insertions and $O(N)$ batch removals, preventing $O(N \log N)$ sorting blocks during hiring phases.
  - Social Homophily similarity matrices utilize categorical bucket-filtering to evaluate mating choices in $O(N)$ time instead of $O(N^2)$.
- **Benchmarks**: Following these optimizations, the engine smoothly processes 5,000 full lifecycle agents in approximately 0.79s per macro-tick on a standard quad-core machine.
- **Persistence Framework**: The simulation supports deep JSON-based checkpointing (`engine.save_checkpoint` / `engine.load_checkpoint`), safely serializing arbitrary class hierarchies, graph relationships, and pseudo-random global generator states to guarantee deterministic resumes across restarts.

---

## 📈 Empirical Validation

Anthropolis evaluates itself not as a theoretical toy, but as a scientifically grounded Digital Twin. We include a specialized automation suite (`simulation/analytics/validate.py`) that executes a 15-year simulation run and outputs `matplotlib` tracking charts mapping the internal outputs directly against the **World Bank 2024 Macroeconomic Targets for India**:
1. **Wealth Inequality**: Simulated Gini Coefficient vs target of ~0.35.
2. **Total Fertility Rate (TFR)**: Simulated empirical TFR vs target of 2.0.
3. **Labor Market**: Simulated Unemployment Rate vs target of ~7.0%.

---

## ⚡ Mathematical Formulations

### 1. Dynamic Fertility (ASFR)
Fertility is restricted to working-age female agents, peaking between ages 20-35. Actual monthly conception probability is friction-modified by education, wealth, and culture:
$$\text{ASFR}_{\text{actual}} = \text{ASFR}_{\text{base}} \times \left(1.0 - \alpha \cdot \text{Education} - \beta \cdot \text{Normalized Wealth}\right) \times \left(0.5 + 1.5 \cdot \text{Religiosity}\right)$$

### 2. Sex-split Gompertz-Makeham Mortality
Monthly probability of death is derived from biological hazards split stochastically by biological sex:
$$P(\text{death}) = 1.0 - e^{-h(x) \cdot dt} \quad \text{where} \quad h(x) = A_s + B_s \cdot c_s^{age}$$
If an agent is starving or in severe poverty, the baseline hazard $A_s$ scales exponentially.

### 3. Social Homophily Mating Index
Conception requires selecting a partner. The probability of choosing partner $j$ scales with their similarity:
$$\text{Similarity}_{ij} = 1.0 - \left[0.1 \cdot |\text{Rel}_{i} - \text{Rel}_{j}| + 0.8 \cdot \mathbb{I}(\text{Affil}_{i} \neq \text{Affil}_{j}) + 0.1 \cdot \text{WealthDiff}\right]$$

### 4. Prospect Theory & Cultural Friction
Agents evaluate financial outcomes not via raw expected utility, but via a reference-dependent loss-aversion curve:
$$V(x) = \begin{cases} x^{0.88} & \text{if } x \ge 0 \\ -\lambda \cdot |x|^{0.88} & \text{if } x < 0 \end{cases}$$
High religiosity scales the loss aversion multiplier for debt, creating profound cultural friction against loans: $\lambda_{\text{debt}} = 2.25 \times (1.0 + 3.0 \cdot \text{Religiosity})$

---

## 💻 The Live Dashboard Frontend

The simulation includes a rich, interactive frontend built with **Streamlit** and **Plotly** (`dashboard.py`). It acts as a real-time monitor for the digital twin, mapping the internal scaled engine (e.g. 1,000+ agents) back to absolute macroeconomic numbers (e.g., 1.46 Billion people).

### Interactive Policy Levers
Users can control the twin in real-time via the sidebar, adjusting variables like:
- **Demographics & Treasury**: Set Population Size (in Crores) and starting Government Treasury (in $ Billions).
- **Economic Constraints**: Modify Base Income Tax, Corporate Tax, Debt Interest Rate, and Universal Basic Income (UBI).
- **Subsidies & Taxes**: Inject behavioral incentives by modifying Grocery Subsidies, Healthcare Subsidies, Education Subsidies, and Fast Food Taxes.

### Live Telemetry Tabs
Once the simulation starts (1 tick per second), the dashboard streams live data:
1. **Economics & Wealth**: Tracks total estate wealth inherited vs escheated, line charts mapping citizen average bank balances vs household debt, and Gini coefficient inequality plots against Private/Public capital.
2. **Health & Wellbeing**: Monitors the dependency ratio, a live SEIR epidemiological curve showing susceptible, exposed, infected, and recovered agent populations, hospital strain percentages, and a 12-month rolling **Infant Mortality Rate**.
3. **Populations & Distributions**: Renders a live **Demographic Age-Sex Pyramid** mapping male and female cohorts with actual alive population telemetry, Sex Ratio at Birth targets, and histograms of population health, age, wealth, and debt distributions.
4. **Environmental Nodes**: Displays the financial capital and employee staffing levels (vs max capacity) of the various macroeconomic nodes (Workplaces, Hospitals, Schools, Grocery Stores) and tracks **Informal Sector Share** metrics.

---

## 🚀 Running the Simulation & Tests

### 1. Prerequisites & Installation
Ensure you have Python 3.8+ installed. Install the dependencies:
```bash
pip install -r requirements.txt
```

### 2. Running the Interactive Dashboard
Launch the Digital Twin with the real-time frame-by-frame rendering frontend:
```bash
streamlit run dashboard.py
```

### 3. Running Automated Tests
Run the core test suite covering all mathematical models, estate inheritance loops, Cobb-Douglas production, and dynamic gestation:
```bash
python3 -m unittest discover -s tests
```
