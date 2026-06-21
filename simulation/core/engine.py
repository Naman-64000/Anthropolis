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
