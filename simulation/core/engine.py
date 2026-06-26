from __future__ import annotations
import random
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
import json

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


def calculate_homophily_similarity(female: Citizen, male: Citizen) -> float:
    """Calculates social homophily mating weight between a female and a male citizen."""
    rel_diff = abs(female.religiosity - male.religiosity)
    aff_diff = 0.0 if female.religious_affiliation == male.religious_affiliation else 1.0
    wealth_diff = min(1.0, abs(female.bank_balance - male.bank_balance) / 2000.0)
    # High homophily (90%+ intra-religion): aff_diff (religious affiliation difference) has high weight
    similarity = 1.0 - (0.1 * rel_diff + 0.8 * aff_diff + 0.1 * wealth_diff)
    return float(max(0.001, similarity))


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

        # Sovereign debt tracker: when government outflows would push government_capital
        # below 0, the overflow is absorbed here instead. Interest accrues monthly.
        self.government_debt: float = 0.0
        # Snapshot of government_capital immediately after initialisation (used for
        # solvency ratio calculations in _adjust_fiscal_policy).
        self.initial_government_capital: float = self.government_capital

        # The 'target' policy values at FULL solvency (>80%). _adjust_fiscal_policy()
        # overrides the active policies each tick on a gradient; the dashboard sliders
        # set these targets, not the live values.
        self._target_policies: Dict[str, Any] = {}

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
            "consumption_tax": 0.05,        # Flat consumption tax on all food/healthcare (GST proxy)
        }

        # Biological & Macroeconomic Calibration Parameters
        self.parameters: Dict[str, float] = {
            "cobb_douglas_alpha": 0.42,
            "cobb_douglas_beta": 0.58,
            "gompertz_A_m": 0.002,
            "gompertz_B_m": 0.00004,
            "gompertz_c_m": 1.095,
            "gompertz_A_f": 0.001,
            "gompertz_B_f": 0.00003,
            "gompertz_c_f": 1.090,
            "asfr_base_peak1": 122.9 / 12000.0,
            "asfr_base_peak2": 112.5 / 12000.0,
            "asfr_base_nonpeak": 35.0 / 12000.0,
        }

        # Initialize lists
        self.citizens: List[Citizen] = []
        self.nodes: List[EnvironmentNode] = []
        self.dead_citizens: List[Citizen] = []

        # Inheritance tracking metrics
        self.total_wealth_inherited: float = 0.0
        self.total_wealth_escheated: float = 0.0
        self.dependency_ratio: float = 0.0

        # Step tax and subsidy trackers
        self.tick_tax_inflow: float = 0.0
        self.tick_income_tax_inflow: float = 0.0
        self.tick_consumption_tax_inflow: float = 0.0
        self.tick_subsidy_outflow: float = 0.0
        self.tick_debt_written_off: float = 0.0
        self.tick_public_bailout_total: float = 0.0
        self.tick_dividends_paid: float = 0.0
        self.tick_sovereign_interest: float = 0.0   # interest cost on government_debt
        self.tick_economic_output: float = 0.0
        self.tick_fdi_inflow: float = 0.0
        self.tick_remittances_inflow: float = 0.0
        self.tick_import_leakage: float = 0.0
        self.tick_citizen_debt_interest: float = 0.0
        self.informal_absorption_rate: float = 0.90

        # Global Macroeconomics (Trade, FDI, Remittances)
        self.foreign_reserves: float = 0.0
        self.fdi_inflow: float = 0.0
        self.remittances_inflow: float = 0.0
        self.trade_balance: float = 0.0

        # Births and infant deaths rolling 12-tick history
        self.births_history: List[int] = []
        self.infant_deaths_history: List[int] = []

        # Metrics historical log
        self.history: List[Dict[str, Any]] = []

        # 1. Instantiate the environment nodes
        self._initialize_nodes()

        # 2. Instantiate population
        self._initialize_population(internal_pop_size)

        # 3. Seed workforce: Assign initial employees to nodes so businesses can operate
        self._seed_initial_workforce()

        # Initialize unemployed_candidates list, pre-sorting it by education_level ascending
        self.unemployed_candidates: List[Citizen] = []
        for c in self.citizens:
            if not c.is_employed and not c.is_student and not c.is_dead and 18.0 <= c.age < 65.0:
                self.unemployed_candidates.append(c)
        self.unemployed_candidates.sort(key=lambda x: x.education_level)

        # Record baseline metrics (Tick 0)
        self._record_metrics()

        # 4. Snapshot initial base prices for nominal fixed subsidies
        grocery_node = self.get_node_by_id("store_fresh")
        hospital_node = self.get_node_by_id("hosp_city")
        self._initial_grocery_base = (grocery_node.price if grocery_node else 20.0) * 20.0
        self._initial_hosp_base = (hospital_node.price if hospital_node else 100.0) * 3.0

    @property
    def grocery_subsidy_fixed(self) -> float:
        return self._initial_grocery_base * abs(self.policies.get("grocery_subsidy", 0.0))

    @property
    def healthcare_subsidy_fixed(self) -> float:
        return self._initial_hosp_base * self.policies.get("healthcare_subsidy", 0.0)

    def to_dict(self) -> dict:
        import random
        r_state = random.getstate()
        r_state_json = [r_state[0], list(r_state[1]), r_state[2]]
        
        np_state = np.random.get_state()
        np_state_json = [np_state[0], np_state[1].tolist(), np_state[2], np_state[3], np_state[4]]
        
        return {
            "tick_count": self.tick_count,
            "next_citizen_id": self.next_citizen_id,
            "pop_scale": getattr(self, "pop_scale", 1.0),
            "government_capital": self.government_capital,
            "government_debt": self.government_debt,
            "initial_government_capital": self.initial_government_capital,
            "_target_policies": self._target_policies,
            "policies": self.policies,
            "parameters": self.parameters,
            "citizens": [c.to_dict() for c in self.citizens],
            "nodes": [n.to_dict() for n in self.nodes],
            "dead_citizens": [c.to_dict() for c in self.dead_citizens],
            "unemployed_candidate_ids": [c.citizen_id for c in self.unemployed_candidates],
            "total_wealth_inherited": self.total_wealth_inherited,
            "total_wealth_escheated": self.total_wealth_escheated,
            "dependency_ratio": self.dependency_ratio,
            "informal_absorption_rate": self.informal_absorption_rate,
            "foreign_reserves": self.foreign_reserves,
            "fdi_inflow": self.fdi_inflow,
            "remittances_inflow": self.remittances_inflow,
            "trade_balance": self.trade_balance,
            "births_history": self.births_history,
            "infant_deaths_history": self.infant_deaths_history,
            "history": self.history,
            "_initial_grocery_base": getattr(self, "_initial_grocery_base", 400.0),
            "_initial_hosp_base": getattr(self, "_initial_hosp_base", 300.0),
            "random_state": r_state_json,
            "np_random_state": np_state_json,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SimulationEngine":
        engine = cls(population_size=150, initial_gov_capital=1000.0, seed=None)
        
        # Override initial state
        engine.tick_count = data.get("tick_count", 0)
        engine.next_citizen_id = data.get("next_citizen_id", 0)
        engine.pop_scale = data.get("pop_scale", 1.0)
        engine.government_capital = data.get("government_capital", 0.0)
        engine.government_debt = data.get("government_debt", 0.0)
        engine.initial_government_capital = data.get("initial_government_capital", 0.0)
        engine._target_policies = data.get("_target_policies", {})
        engine.policies = data.get("policies", {})
        if "parameters" in data:
            engine.parameters = data["parameters"]
        
        # Reconstruct Citizens
        engine.citizens = [Citizen.from_dict(c_data) for c_data in data.get("citizens", [])]
        engine.dead_citizens = [Citizen.from_dict(c_data) for c_data in data.get("dead_citizens", [])]
        
        # Reconstruct Nodes
        engine.nodes = [EnvironmentNode.from_dict(n_data) for n_data in data.get("nodes", [])]
        
        # Link employees to nodes
        citizen_map = {c.citizen_id: c for c in engine.citizens}
        for node in engine.nodes:
            if hasattr(node, "_pending_employee_ids"):
                node.employees = [citizen_map[cid] for cid in node._pending_employee_ids if cid in citizen_map]
                delattr(node, "_pending_employee_ids")
        
        # Rebuild unemployed candidates list using exactly the saved order
        if "unemployed_candidate_ids" in data:
            engine.unemployed_candidates = [citizen_map[cid] for cid in data["unemployed_candidate_ids"] if cid in citizen_map]
        else:
            engine.unemployed_candidates = []
            for c in engine.citizens:
                if not c.is_employed and not c.is_student and not c.is_dead and 18.0 <= c.age < 65.0:
                    engine.unemployed_candidates.append(c)
            engine.unemployed_candidates.sort(key=lambda x: x.education_level)
            
        # Restore metrics
        engine.total_wealth_inherited = data.get("total_wealth_inherited", 0.0)
        engine.total_wealth_escheated = data.get("total_wealth_escheated", 0.0)
        engine.dependency_ratio = data.get("dependency_ratio", 0.0)
        engine.informal_absorption_rate = data.get("informal_absorption_rate", 0.90)
        
        # Restore Macro Trade metrics
        engine.foreign_reserves = data.get("foreign_reserves", 0.0)
        engine.fdi_inflow = data.get("fdi_inflow", 0.0)
        engine.remittances_inflow = data.get("remittances_inflow", 0.0)
        engine.trade_balance = data.get("trade_balance", 0.0)
        
        engine.births_history = data.get("births_history", [])
        engine.infant_deaths_history = data.get("infant_deaths_history", [])
        engine.history = data.get("history", [])
        
        # Restore bases
        engine._initial_grocery_base = data.get("_initial_grocery_base", 400.0)
        engine._initial_hosp_base = data.get("_initial_hosp_base", 300.0)
        
        # Restore random states
        import random
        if "random_state" in data:
            rs = data["random_state"]
            r_state = (rs[0], tuple(rs[1]), rs[2])
            random.setstate(r_state)
            
        if "np_random_state" in data:
            ns = data["np_random_state"]
            np_state = (ns[0], np.array(ns[1], dtype=np.uint32), ns[2], ns[3], ns[4])
            np.random.set_state(np_state)
            
        return engine

    def save_checkpoint(self, filepath: str) -> None:
        """Serializes the engine state to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f)

    @classmethod
    def load_checkpoint(cls, filepath: str) -> "SimulationEngine":
        """Deserializes the engine state from a JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def _initialize_nodes(self) -> None:
        """Creates default environment nodes in the city, calibrated to India workforce sector distributions."""
        self.nodes = [
            # --- RURAL NODES ---
            # Agriculture sector (Informal)
            Workplace(node_id="wp_farm_rural", node_name="Rural Co-op Farm", capacity=200, employee_capacity=42, location="Rural", is_informal=True),
            # Rural Services
            School(node_id="school_rural", node_name="Village Public School", capacity=100, employee_capacity=5, location="Rural", is_informal=False),
            Hospital(node_id="hosp_rural", node_name="Village Clinic", capacity=50, employee_capacity=2, location="Rural", is_informal=False),
            GroceryStore(node_id="store_rural", node_name="Village Mandi", capacity=200, employee_capacity=5, location="Rural", is_informal=True),
            
            # --- URBAN NODES ---
            # Industry & Services (Formal)
            Workplace(node_id="wp_factory_urban", node_name="Urban Textile Mill", capacity=150, employee_capacity=21, location="Urban", is_informal=False),
            Hospital(node_id="hosp_urban", node_name="City General Hospital", capacity=50, employee_capacity=3, location="Urban", is_informal=False),
            School(node_id="school_urban", node_name="City Public School", capacity=100, employee_capacity=5, location="Urban", is_informal=False),
            GroceryStore(node_id="store_urban", node_name="Urban Supermarket", capacity=200, employee_capacity=5, location="Urban", is_informal=False),
            
            # Urban Informal Sector
            Restaurant(node_id="rest_street", node_name="Street Food Stall", capacity=200, employee_capacity=7, location="Urban", is_informal=True),
        ]

    def _initialize_population(self, size: int) -> None:
        """
        Generates the starting citizen population with a realistic demographic pyramid and sex ratio.
        
        Note on bank_balance seeding: bank_balance represents liquid savings only, not total household 
        wealth. sigma=1.72 produces a lognormal Gini of ~erf(sigma/2) = 0.77 at initialization, 
        consistent with India's extreme liquid savings concentration. The simulated Gini compresses 
        toward ~0.40 over 180 ticks as wages and welfare lift the bottom cohort -- this compression 
        represents the model's economic mobility dynamics, not a calibration error.
        """
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

            # Geographic Location & Caste
            location = random.choices(["Urban", "Rural"], weights=[35.0, 65.0], k=1)[0]
            caste = random.choices(["General", "OBC", "SC", "ST"], weights=[30.0, 40.0, 20.0, 10.0], k=1)[0]

            # Economic parameters scale with age/productivity
            if age < 18.0:
                bank_balance = 0.0
                education_level = 0.0
                debt = 0.0
            else:
                # Bank balance (liquid savings) centers around Median $1712 (lognormal mu=7.445, sigma=1.72)
                bank_balance = float(np.clip(np.random.lognormal(mean=7.445, sigma=1.72), 200.0, 100000.0))
                
                # Structural Caste Inequality in Education
                if caste == "General":
                    education_level = float(np.random.beta(6, 4))
                elif caste == "OBC":
                    education_level = float(np.random.beta(4, 5))
                elif caste == "SC":
                    education_level = float(np.random.beta(3, 6))
                else: # ST
                    education_level = float(np.random.beta(2, 7))
                # Household debt conditional on savings: real average debt-to-asset ratio is ~35%
                # We use beta(3.5, 6.5) which centers around 0.35, ensuring debt rarely exceeds savings
                debt_ratio = float(np.random.beta(3.5, 6.5))
                debt = bank_balance * debt_ratio

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
                religiosity=religiosity,
                location=location,
                caste=caste,
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

    def register_unemployed(self, citizen: Citizen) -> None:
        """Adds citizen to pre-sorted unemployed list if not already present."""
        if citizen in self.unemployed_candidates:
            return
        
        # Binary search for insertion point to keep list sorted by education_level ascending
        edu = citizen.education_level
        low = 0
        high = len(self.unemployed_candidates)
        while low < high:
            mid = (low + high) // 2
            if self.unemployed_candidates[mid].education_level < edu:
                low = mid + 1
            else:
                high = mid
        self.unemployed_candidates.insert(low, citizen)

    def unregister_unemployed(self, citizen: Citizen) -> None:
        """Removes citizen from pre-sorted unemployed list if present."""
        try:
            self.unemployed_candidates.remove(citizen)
        except ValueError:
            pass

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
        
        # Clean up node employee lists to only contain living citizens present in self.citizens
        citizen_set = {c for c in self.citizens if not c.is_dead}
        for node in self.nodes:
            node.employees = [e for e in node.employees if e in citizen_set]

        # Reset and sync unemployed candidates list with current citizens
        self.unemployed_candidates = []
        for c in self.citizens:
            if not c.is_employed and not c.is_student and not c.is_dead and 18.0 <= c.age < 65.0:
                self.unemployed_candidates.append(c)
        self.unemployed_candidates.sort(key=lambda x: x.education_level)
        
        self.tick_tax_inflow = 0.0
        self.tick_income_tax_inflow = 0.0
        self.tick_consumption_tax_inflow = 0.0
        self.tick_subsidy_outflow = 0.0
        self.tick_debt_written_off = 0.0
        self.tick_public_bailout_total = 0.0
        self.tick_dividends_paid = 0.0
        self.tick_sovereign_interest = 0.0
        self.tick_economic_output = 0.0
        self.tick_fdi_inflow = 0.0
        self.tick_remittances_inflow = 0.0
        self.tick_import_leakage = 0.0
        self.tick_citizen_debt_interest = 0.0

        # --- Sovereign interest cost ---
        # 6.5% annual G-sec yield / 12 = 0.5417% monthly, charged on outstanding government_debt.
        if self.government_debt > 0.0:
            monthly_rate = 0.065 / 12.0
            interest = self.government_debt * monthly_rate
            # Interest is paid from government_capital; if that's also depleted,
            # it compounds onto government_debt (capitalized interest).
            self._gov_spend(interest)
            self.government_debt += interest   # interest accrues to the debt balance
            self.tick_sovereign_interest = interest

        # --- Graduated fiscal policy adjustment ---
        # Must run before ANY spending this tick so that subsidy rates already
        # reflect the current fiscal state when citizen.tick() reads them.
        self._adjust_fiscal_policy()

        self.tick_births_count = 0
        self.tick_infant_deaths_count = 0
        
        prev_money = self._calculate_total_money()

        # Calculate dependency ratio
        working = [c for c in self.citizens if not c.is_dead and 18.0 <= c.age < 65.0]
        dependents = [c for c in self.citizens if not c.is_dead and (c.age < 18.0 or c.age >= 65.0)]
        self.dependency_ratio = len(dependents) / len(working) if working else 0.0

        # Apply welfare stipends and UBI
        self._apply_welfare_and_ubi()

        # =========================================================================
        # ORDERING DEPENDENCY WARNING:
        # The execution order of the following updates is critical for tax collection:
        # 1. citizen.tick() resets citizen.daily_earnings to 0.0.
        # 2. node.tick() pays wages, calling citizen.receive_wage() to set daily_earnings.
        # 3. _collect_income_taxes() taxes citizens based on daily_earnings.
        # Changing this sequence will break the income tax collection mechanism.
        # =========================================================================

        # Reset hospital admission slots for this month BEFORE citizens act.
        # occupied_slots must be 0 at the start of each citizen tick so that
        # admit_patient() calls during citizen.tick() accumulate from scratch.
        # The reset cannot live in node.tick() (which runs AFTER citizen.tick())
        # because that would wipe counts before _record_metrics() samples them.
        for node in self.nodes:
            node.occupied_slots = 0

        # 1. Update Citizens Concurrently
        import concurrent.futures
        
        # We use a ThreadPoolExecutor to evaluate citizens concurrently. 
        # While the GIL restricts true multiprocessing, this introduces a scalable
        # concurrent architecture and speeds up I/O or C-extension bound steps.
        # Future iterations can swap to ProcessPoolExecutor once the state is fully decoupled.
        def _tick_citizen(c):
            if not c.is_dead:
                c.daily_earnings = 0.0
                c.last_dividend = 0.0
                c.tick(self)
                
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(_tick_citizen, self.citizens)

        # Mating and Fertility loop
        self._execute_mating_and_fertility()

        # 2. Update Environment Nodes (Production & Wages paid here)
        for node in self.nodes:
            node.tick(self)

        # 2b. Government bailout for distressed public-service nodes (Hospital / School)
        # Must run AFTER node.tick() (so wages/firing have already been settled) and
        # BEFORE informal-sector absorption + tax collection so that newly bailed-out
        # nodes can attempt hiring in the same tick via _attempt_hiring().
        self._execute_public_service_bailouts()

        # Execute Informal Sector self-employment absorption
        self._execute_informal_sector()

        # 3. Apply Income Taxes with dependency scaling
        self._collect_income_taxes()
        
        # 4. Inject global remittances
        self._process_remittances()

        # Handle Deceased Citizens & inheritance
        self._reconcile_deaths()

        # Aggregate dividends paid by workplaces this tick
        self.tick_dividends_paid = sum(node.monthly_dividends for node in self.nodes)

        # Update births and infant deaths histories
        self.births_history.append(self.tick_births_count)
        self.infant_deaths_history.append(self.tick_infant_deaths_count)
        if len(self.births_history) > 12:
            self.births_history.pop(0)
            self.infant_deaths_history.pop(0)

        # Aggregate analytics
        self._record_metrics()
        
        # Verify Money Conservation
        current_money = self._calculate_total_money()
        delta = current_money - prev_money
        expected_delta = (
            self.tick_economic_output 
            + self.tick_fdi_inflow 
            + self.tick_remittances_inflow 
            - self.tick_import_leakage 
            - self.tick_citizen_debt_interest 
            + self.tick_debt_written_off
        )
        print(
            f"[Tick {self.tick_count}] "
            f"Gov Tax Inflow: ${self.tick_tax_inflow:,.2f} | "
            f"Gov Subsidy/UBI Outflow: ${self.tick_subsidy_outflow:,.2f} | "
            f"Public Node Bailout: ${self.tick_public_bailout_total:,.2f} | "
            f"Dividends Paid: ${self.tick_dividends_paid:,.2f} | "
            f"Sov Interest: ${self.tick_sovereign_interest:,.2f} | "
            f"Gov Debt: ${self.government_debt:,.2f}"
        )
        print(f"[Tick {self.tick_count}] Money Conservation Delta: ${delta:,.2f} (Expected: ${expected_delta:,.2f})")
        
        if abs(delta - expected_delta) > 0.10:
            raise AssertionError(
                f"Financial Integrity Violation: Money conservation failed on tick {self.tick_count}. "
                f"Actual delta: ${delta:,.2f}, Expected: ${expected_delta:,.2f}. "
                f"Discrepancy: ${abs(delta - expected_delta):,.2f}"
            )

        # Verify tax collection ordering correctness (Safeguard Check)
        total_wages_paid = sum(node.monthly_wages for node in self.nodes)
        tax_rate = self.policies.get("tax_rate", 0.15)
        if total_wages_paid > 0.0 and tax_rate > 0.0 and getattr(self, "tick_income_tax_inflow", 0.0) == 0.0:
            working_earners = [c for c in self.citizens if not c.is_dead and (18.0 <= c.age < 65.0) and c.daily_earnings > 0.0]
            if working_earners:
                raise AssertionError(
                    "Income tax collection failed: wages were paid to working-age citizens but zero tax was collected. "
                    "This indicates that the sequence of citizen.tick(), node.tick(), and _collect_income_taxes() "
                    "in SimulationEngine.step() has been incorrectly reordered."
                )

    def _adjust_fiscal_policy(self) -> None:
        """Graduated fiscal stabilizer: adjusts subsidies based on current solvency ratio."""
        # Snapshot the current values to _target_policies if missing
        for k in ["grocery_subsidy", "healthcare_subsidy", "free_emergency_care"]:
            if k not in self._target_policies:
                self._target_policies[k] = self.policies[k]

        target_grocery = self._target_policies["grocery_subsidy"]
        target_health = self._target_policies["healthcare_subsidy"]
        target_free_er = self._target_policies["free_emergency_care"]

        total_obligations = self.government_capital + self.government_debt
        solvency = self.government_capital / total_obligations if total_obligations > 0 else 1.0

        if solvency > 0.80:
            self.policies["grocery_subsidy"] = target_grocery
            self.policies["healthcare_subsidy"] = target_health
            self.policies["free_emergency_care"] = target_free_er
        elif solvency > 0.60:
            self.policies["grocery_subsidy"] = max(target_grocery, -0.60)
            self.policies["healthcare_subsidy"] = min(target_health, 0.25)
            self.policies["free_emergency_care"] = target_free_er
        elif solvency > 0.40:
            self.policies["grocery_subsidy"] = max(target_grocery, -0.40)
            self.policies["healthcare_subsidy"] = min(target_health, 0.15)
            self.policies["free_emergency_care"] = False
        elif solvency > 0.20:
            self.policies["grocery_subsidy"] = max(target_grocery, -0.20)
            self.policies["healthcare_subsidy"] = min(target_health, 0.10)
            self.policies["free_emergency_care"] = False
        else:
            self.policies["grocery_subsidy"] = max(target_grocery, 0.0)
            self.policies["healthcare_subsidy"] = min(target_health, 0.05)
            self.policies["free_emergency_care"] = False

    def _gov_spend(self, amount: float) -> float:
        """
        Deducts `amount` from government_capital, flooring at 0.0.  Any portion
        that would push government_capital below zero is added to government_debt
        instead, representing sovereign borrowing.  Returns the actual amount
        deducted from government_capital (may be less than `amount`).
        """
        if amount <= 0.0:
            return 0.0
        actual = min(amount, self.government_capital)
        self.government_capital -= actual
        overflow = amount - actual
        if overflow > 0.0:
            self.government_debt += overflow
        return actual

    def _calculate_total_money(self) -> float:
        total_citizen_balance = sum(c.bank_balance for c in self.citizens if not c.is_dead)
        total_citizen_debt = sum(c.debt for c in self.citizens if not c.is_dead)
        total_node_capital = sum(n.capital for n in self.nodes)
        # Subtract government_debt: sovereign borrowing is a liability on the money supply
        return (self.government_capital + total_node_capital
                + total_citizen_balance - total_citizen_debt
                - self.government_debt)

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
                        self._gov_spend(share)
                        self.tick_subsidy_outflow += share
                else:
                    c.bank_balance += 15.0
                    self._gov_spend(15.0)
                    self.tick_subsidy_outflow += 15.0

        # 2. Universal Basic Income
        ubi = self.policies.get("ubi_amount", 0.0)
        if ubi > 0.0:
            for citizen in self.citizens:
                if not citizen.is_dead:
                    self._gov_spend(ubi)
                    self.tick_subsidy_outflow += ubi
                    citizen.bank_balance += ubi

    def _execute_public_service_bailouts(self) -> None:
        """
        Government bailout for distressed Hospital and School nodes.

        If a public-service node's capital falls below the *operational floor*
        — defined as the full monthly wage bill it would pay if running at
        100% employee capacity at current prices — AND the node is staffed at
        fewer than 50% of its employee_capacity, it is classified as being in
        public-service distress.  The government injects exactly enough capital
        to bring the node back to that floor.

        The transfer is:
          - Deducted from self.government_capital (no free money).
          - Accumulated in self.tick_public_bailout_total (appears in the
            per-tick log so the money-conservation check stays honest).
          - Tracked with node.received_bailout_this_tick = True so the node's
            hire_employee() can bypass the revenue-history gate and hire a
            skeleton crew in the same tick.

        This mirrors real-world government budget allocations to public health
        and education services when they are at risk of operational closure.
        """
        PUBLIC_NODE_TYPES = ("Hospital", "School")

        for node in self.nodes:
            if node.node_type not in PUBLIC_NODE_TYPES:
                continue

            # --- Compute the operational floor dynamically ---
            # calculate_wage() reads only citizen.education_level from the
            # citizen argument; use a lightweight stub at median education (0.45)
            # to estimate average monthly cost per employee at current prices.
            import types as _types
            _ref = _types.SimpleNamespace(education_level=0.45)
            wage_per_head = node.calculate_wage(_ref)
            # Floor = one full month of wages at full capacity
            operational_floor = wage_per_head * node.employee_capacity

            staff_fill_rate = (
                len(node.employees) / node.employee_capacity
                if node.employee_capacity > 0 else 1.0
            )

            # Only bail out if BOTH conditions are met:
            #   1. Capital is below the operational floor.
            #   2. Staff fill rate is below 50% (structural distress, not a
            #      routine low-capital month for a well-staffed node).
            if node.capital < operational_floor and staff_fill_rate < 0.5:
                injection = operational_floor - node.capital
                # Guard: we no longer cap by government_capital directly since _gov_spend
                # handles overflow to government_debt, but we still ensure bailout isn't arbitrary.
                if injection > 0.0:
                    node.capital += injection
                    self._gov_spend(injection)
                    self.tick_public_bailout_total += injection
                    node.received_bailout_this_tick = True

                    # Immediately trigger hiring so the node can staff up
                    # this same tick rather than waiting until next month.
                    if len(node.employees) < node.employee_capacity:
                        node._attempt_hiring(self)

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
            males_by_religion = {}
            for male in eligible_males:
                males_by_religion.setdefault(male.religious_affiliation, []).append(male)

            for female in eligible_females:
                age = female.age
                if 20.0 <= age < 25.0:
                    asfr_base = self.parameters.get("asfr_base_peak1", 122.9 / 12000.0)
                elif 25.0 <= age < 30.0:
                    asfr_base = self.parameters.get("asfr_base_peak2", 112.5 / 12000.0)
                elif 15.0 <= age < 20.0 or 30.0 <= age <= 45.0:
                    asfr_base = self.parameters.get("asfr_base_nonpeak", 35.0 / 12000.0)
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
                    # Select male partner using Social Homophily similarity weights from a pre-filtered pool
                    female_religion = female.religious_affiliation
                    same_religion_males = males_by_religion.get(female_religion, [])
                    
                    cross_religion_males = []
                    for rel, males in males_by_religion.items():
                        if rel != female_religion:
                            cross_religion_males.extend(males)
                    
                    num_cross = len(cross_religion_males)
                    sample_size = int(num_cross * 0.1)
                    if sample_size == 0 and num_cross > 0:
                        if random.random() < 0.1:
                            sample_size = 1
                    
                    selected_cross = random.sample(cross_religion_males, sample_size) if sample_size > 0 else []
                    candidate_males = same_religion_males + selected_cross
                    
                    if not candidate_males:
                        candidate_males = eligible_males
                    
                    male_weights = []
                    for male in candidate_males:
                        similarity = calculate_homophily_similarity(female, male)
                        male_weights.append(similarity)
                    
                    partner = random.choices(candidate_males, weights=male_weights, k=1)[0]
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

                        # Stochastic risk tolerance inheritance (correlating with parents)
                        father_risk = father.risk_tolerance if father else citizen.risk_tolerance
                        avg_risk = (citizen.risk_tolerance + father_risk) / 2.0
                        child_risk = float(np.clip(np.random.normal(avg_risk, 0.1), 0.0, 1.0))

                        child_id = self.next_citizen_id
                        self.next_citizen_id += 1
                        
                        child = Citizen(
                            citizen_id=child_id,
                            age=0.0,
                            baseline_health=float(np.clip(np.random.normal(70.8, 5.0), 50.0, 100.0)),
                            education_level=0.0,
                            risk_tolerance=child_risk,
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
        self.tick_births_count = len(newborns)

    def _execute_informal_sector(self) -> None:
        """Stochastically absorbs eligible unemployed adults into self-employment (informal sector)."""
        for citizen in self.citizens:
            if citizen.is_dead:
                continue
            
            # Formally employed citizens cannot be informal
            if citizen.is_employed:
                citizen.is_informal = False
                continue
                
            # Eligible adults: working age and not a student
            if (18.0 <= citizen.age < 65.0) and not citizen.is_student:
                # Stochastic absorption rate based on education (ranges from 0.90 to 0.50)
                p_absorb = (0.90 - 0.40 * citizen.education_level) * self.informal_absorption_rate
                if random.random() < p_absorb:
                    citizen.is_informal = True
                    # Weakened education wage dependence & higher variance (+/- 50%)
                    base_wage = (3.5 + citizen.education_level * 1.0) * 0.45
                    wage = base_wage * random.uniform(0.5, 1.5)
                    # Scale informal wages with general monthly price inflation factor
                    inflation_factor = (1.0 + (0.0475 / 12.0)) ** self.tick_count
                    monthly_wage = wage * 20.0 * inflation_factor
                    citizen.bank_balance += monthly_wage
                    citizen.daily_earnings = monthly_wage
                    self.tick_economic_output += monthly_wage
                else:
                    citizen.is_informal = False
                    citizen.daily_earnings = 0.0
            else:
                citizen.is_informal = False

    def _process_remittances(self) -> None:
        """Injects stochastic foreign remittances to a subset of citizens."""
        for citizen in self.citizens:
            if not citizen.is_dead and 18.0 <= citizen.age:
                # 1.5% of working age citizens receive remittances monthly
                if random.random() < 0.015:
                    remittance = float(np.random.lognormal(mean=6.0, sigma=1.2)) # Mean ~$400
                    citizen.bank_balance += remittance
                    self.remittances_inflow += remittance
                    self.tick_remittances_inflow += remittance
                    
    def _collect_income_taxes(self) -> None:
        """Deducts income tax from citizen daily earnings and transfers to government capital, scaled by dependency ratio."""
        tax_rate = self.policies.get("tax_rate", 0.15)
        effective_tax_rate = tax_rate + min(0.08, 0.10 * self.dependency_ratio)
        effective_tax_rate = min(0.9, effective_tax_rate)  # Cap tax rate at 90%

        if effective_tax_rate > 0.0:
            for citizen in self.citizens:
                if not citizen.is_dead and (18.0 <= citizen.age < 65.0) and citizen.daily_earnings > 0.0:
                    tax_rate_for_citizen = effective_tax_rate
                    if getattr(citizen, "is_informal", False):
                        # Zero tax compliance in the informal sector
                        tax_rate_for_citizen = 0.0
                        
                    tax_amount = citizen.daily_earnings * tax_rate_for_citizen
                    tax_amount = min(tax_amount, citizen.bank_balance)
                    citizen.bank_balance -= tax_amount
                    self.government_capital += tax_amount
                    self.tick_tax_inflow += tax_amount
                    self.tick_income_tax_inflow += tax_amount

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
            
            # Ensure they are removed from the unemployed candidates list
            self.unregister_unemployed(citizen)
            
            # Execute Inheritance Protocol
            self._execute_inheritance(citizen)

            # Move to dead log
            self.dead_citizens.append(citizen)

        self.citizens = active_alive
        self.tick_infant_deaths_count = sum(1 for c in newly_dead if c.age < 1.0)

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
        metrics = calculate_macro_metrics(
            self.citizens, 
            self.nodes, 
            self.dead_citizens,
            births_window=self.births_history,
            infant_deaths_window=self.infant_deaths_history
        )
        # Add metadata
        metrics["tick"] = self.tick_count
        metrics["government_capital"] = self.government_capital
        metrics["government_debt"] = self.government_debt
        # Sum capital of all businesses
        metrics["private_capital"] = sum(node.capital for node in self.nodes)
        metrics["tick_dividends_paid"] = self.tick_dividends_paid
        metrics["fiscal_solvency"] = (
            self.government_capital / (self.government_capital + self.government_debt)
            if (self.government_capital + self.government_debt) > 0 else 1.0
        )
        
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
        Locates the environment node of the specified type in the citizen's location,
        preferring informal nodes if the citizen is an informal worker.
        """
        loc = getattr(citizen, "location", "Urban")
        is_informal = getattr(citizen, "is_informal", False)
        
        candidates = [n for n in self.nodes if n.node_type == node_type and getattr(n, "location", "Urban") == loc]
        
        if is_informal:
            informal_candidates = [n for n in candidates if getattr(n, "is_informal", False)]
            if informal_candidates:
                candidates = informal_candidates
        else:
            formal_candidates = [n for n in candidates if not getattr(n, "is_informal", False)]
            if formal_candidates:
                candidates = formal_candidates
                
        if not candidates:
            # Fallback to any location if strict geographic/formal matching fails
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

    def get_nodes_with_job_openings(self, citizen: Citizen = None) -> List[EnvironmentNode]:
        """Returns a list of environmental nodes with vacant employee slots."""
        openings = [
            n for n in self.nodes 
            if len(n.employees) < n.employee_capacity
        ]
        if citizen:
            loc = getattr(citizen, "location", "Urban")
            local_openings = [n for n in openings if getattr(n, "location", "Urban") == loc]
            if local_openings:
                return local_openings
        return openings

    def get_node_by_id(self, node_id: str) -> Optional[EnvironmentNode]:
        """Helper to find an environment node by its ID."""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def receive_tax(self, amount: float, tax_type: str = "general") -> None:
        """Callback for corporate and citizen taxes."""
        self.government_capital += amount
        self.tick_tax_inflow += amount
        if tax_type == "consumption":
            self.tick_consumption_tax_inflow += amount
        elif tax_type == "income":
            self.tick_income_tax_inflow += amount

    def get_history_dataframe(self) -> pd.DataFrame:
        """Converts recorded tick history to a pandas DataFrame."""
        return pd.DataFrame(self.history)
