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
    A_s: Optional[float] = None,
    B_s: Optional[float] = None,
    c_val: Optional[float] = None,
) -> float:
    """Gompertz-Makeham Law of Mortality scaled to monthly tick with poverty multipliers."""
    if A_s is None:
        A_s = 0.002 if sex == 'M' else 0.001
    if B_s is None:
        B_s = 0.00004 if sex == 'M' else 0.00003
    if c_val is None:
        c_val = 1.095 if sex == 'M' else 1.090

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
        location: str = 'Rural',
        caste: str = 'General',
    ) -> None:
        self.citizen_id: int = citizen_id
        self.age: float = age
        self.baseline_health: float = baseline_health
        self.education_level: float = max(0.0, min(1.0, education_level))
        self.risk_tolerance: float = risk_tolerance

        # New Socio-Economic and Geographic attributes
        self.location: str = location
        self.caste: str = caste
        self.months_unemployed: int = 0

        self.health: float = baseline_health
        self.energy: float = 2458.0
        self.bank_balance: float = bank_balance
        self.stress_level: float = 14.0
        self.debt: float = 1280.0

        self.is_employed: bool = False
        self.employer_id: Optional[str] = None
        self.is_student: bool = False
        self.is_informal: bool = False
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
        self.last_dividend: float = 0.0
        self.total_dividends_received: float = 0.0

    def to_dict(self) -> dict:
        return {
            "citizen_id": self.citizen_id,
            "age": self.age,
            "baseline_health": self.baseline_health,
            "education_level": self.education_level,
            "risk_tolerance": self.risk_tolerance,
            "health": self.health,
            "energy": self.energy,
            "bank_balance": self.bank_balance,
            "stress_level": self.stress_level,
            "debt": self.debt,
            "is_employed": self.is_employed,
            "employer_id": self.employer_id,
            "is_student": self.is_student,
            "is_informal": self.is_informal,
            "is_dead": self.is_dead,
            "cause_of_death": self.cause_of_death,
            "seir_state": self.seir_state,
            "infection_days": self.infection_days,
            "sex": self.sex,
            "parent_ids": self.parent_ids,
            "offspring_ids": self.offspring_ids,
            "is_pregnant": self.is_pregnant,
            "gestation_months": self.gestation_months,
            "birth_cooldown": self.birth_cooldown,
            "religious_affiliation": self.religious_affiliation,
            "religiosity": self.religiosity,
            "location": self.location,
            "caste": self.caste,
            "months_unemployed": self.months_unemployed,
            "total_earnings": self.total_earnings,
            "total_spending": self.total_spending,
            "work_experience": self.work_experience,
            "daily_earnings": self.daily_earnings,
            "last_monthly_income": self.last_monthly_income,
            "last_dividend": self.last_dividend,
            "total_dividends_received": self.total_dividends_received,
            "temp_partner_id": getattr(self, "temp_partner_id", -1),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Citizen":
        citizen = cls(
            citizen_id=data["citizen_id"],
            age=data["age"],
            baseline_health=data["baseline_health"],
            education_level=data["education_level"],
            risk_tolerance=data["risk_tolerance"],
            bank_balance=data["bank_balance"],
            sex=data["sex"],
            parent_ids=data["parent_ids"],
            religious_affiliation=data["religious_affiliation"],
            religiosity=data["religiosity"],
            location=data.get("location", "Rural"),
            caste=data.get("caste", "General"),
        )
        citizen.health = data["health"]
        citizen.energy = data["energy"]
        citizen.stress_level = data["stress_level"]
        citizen.debt = data["debt"]
        citizen.is_employed = data["is_employed"]
        citizen.employer_id = data["employer_id"]
        citizen.is_student = data["is_student"]
        citizen.is_informal = data["is_informal"]
        citizen.is_dead = data["is_dead"]
        citizen.cause_of_death = data["cause_of_death"]
        citizen.seir_state = data["seir_state"]
        citizen.infection_days = data["infection_days"]
        citizen.offspring_ids = data["offspring_ids"]
        citizen.is_pregnant = data["is_pregnant"]
        citizen.gestation_months = data["gestation_months"]
        citizen.birth_cooldown = data["birth_cooldown"]
        citizen.total_earnings = data["total_earnings"]
        citizen.total_spending = data["total_spending"]
        citizen.work_experience = data.get("work_experience", 0)
        citizen.daily_earnings = data.get("daily_earnings", 0.0)
        citizen.last_monthly_income = data.get("last_monthly_income", 0.0)
        citizen.last_dividend = data.get("last_dividend", 0.0)
        citizen.total_dividends_received = data.get("total_dividends_received", 0.0)
        citizen.months_unemployed = data.get("months_unemployed", 0)
        if "temp_partner_id" in data:
            citizen.temp_partner_id = data["temp_partner_id"]
        return citizen

    @property
    def net_worth(self) -> float:
        return self.bank_balance - self.debt

    def tick(self, engine: "SimulationEngine") -> None:
        if self.is_dead:
            return

        was_youth = (self.age) < 18.0

        # 1. Biological and Age Updates
        self.age += 1.0 / 12.0
        self._apply_decays(engine)

        if self.is_dead:
            return

        # 2. SEIR Epidemic Progression
        self._update_seir_state()

        # Enforce geriatric retirement when turning 65
        if self.age >= 65.0:
            if self.is_employed:
                self.lose_job(engine)
            else:
                engine.unregister_unemployed(self)

        # Infants and Youths are dependents
        if self.age < 18.0:
            self._service_dependent_needs(engine)
            return
        elif self.is_student:
            self.is_student = False  # Graduate at age 18
            engine.register_unemployed(self)
        elif was_youth:
            # Just turned 18 and wasn't a student
            engine.register_unemployed(self)

        # 3. Financial Debt Mechanics (Adults only)
        self._service_debt(engine)

        # 4. Decision-Making Loop using Prospect Theory (Adults/Geriatrics)
        self._make_decisions(engine)

    def _apply_decays(self, engine: "SimulationEngine") -> None:
        """Applies energy drain, stress, and checks Gompertz-Makeham mortality."""
        # Monthly non-linear energy drain scaled to 2458.0 kcal capacity
        energy_loss = (50.0 + (15.0 * np.exp(1.0 - self.health / 70.8))) * 24.58
        self.energy = max(0.0, self.energy - energy_loss)

        if self.sex == 'M':
            A_s = engine.parameters.get("gompertz_A_m", 0.002)
            B_s = engine.parameters.get("gompertz_B_m", 0.00004)
            c_val = engine.parameters.get("gompertz_c_m", 1.095)
        else:
            A_s = engine.parameters.get("gompertz_A_f", 0.001)
            B_s = engine.parameters.get("gompertz_B_f", 0.00003)
            c_val = engine.parameters.get("gompertz_c_f", 1.090)

        # Gompertz-Makeham Mortality Calculation (monthly)
        mortality_prob = calculate_monthly_mortality_prob(self.age, self.sex, self.energy, self.net_worth, A_s, B_s, c_val)
        
        # Adjust mortality hazard based on health and SEIR state
        if self.health < 20.0:
            mortality_prob *= 1.5

        if self.seir_state == 'I':
            mortality_prob *= 2.0  # Increased hazard during infection
            
        # Migration logic
        if self.location == "Rural" and not self.is_employed and self.months_unemployed > 6 and 18.0 <= self.age < 65.0:
            migration_chance = 0.15
            
            # Network effects (Chain Migration)
            has_urban_family = False
            family_ids = self.parent_ids + self.offspring_ids
            for fid in family_ids:
                fam = engine.get_citizen_by_id(fid)
                if fam and not fam.is_dead and getattr(fam, "location", "Rural") == "Urban":
                    has_urban_family = True
                    break
            
            if has_urban_family:
                migration_chance = 0.65  # Massive network boost
                
            if np.random.random() < migration_chance:
                self.location = "Urban"
                self.months_unemployed = 0

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
            self.die(cause, engine)
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
        if 5.0 <= self.age < 18.0:
            school = engine.get_best_available_node("School", self)
            if school:
                base_tuition = school.price * 10.0  # Monthly scaled tuition
                subsidy_rate = engine.policies.get("education_subsidy", 0.0)
                subsidy_amount = base_tuition * subsidy_rate
                tuition_paid_by_citizen = base_tuition - subsidy_amount
                
                paid = False
                for parent in alive_parents:
                    if parent.bank_balance >= tuition_paid_by_citizen:
                        parent.bank_balance -= tuition_paid_by_citizen
                        parent.total_spending += tuition_paid_by_citizen
                        self.is_student = True
                        school.receive_revenue(base_tuition, parent)
                        engine._gov_spend(subsidy_amount)
                        engine.tick_subsidy_outflow += subsidy_amount
                        paid = True
                        break
                
                if not paid:
                    self.is_student = False

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
                        if not getattr(grocery_store, "is_informal", False):
                            c_tax = base_p_grocery * engine.policies.get("consumption_tax", 0.0)
                            grocery_store.capital -= c_tax
                            engine.receive_tax(c_tax, tax_type="consumption")
                        
                        import_leak = base_p_grocery * 0.05
                        grocery_store.capital -= import_leak
                        engine.trade_balance -= import_leak
                        engine.tick_import_leakage += import_leak
                        engine._gov_spend(subsidy_amount)
                        engine.tick_subsidy_outflow += subsidy_amount
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
                            if not getattr(restaurant, "is_informal", False):
                                c_tax = base_p_fast * engine.policies.get("consumption_tax", 0.0)
                                restaurant.capital -= c_tax
                                engine.receive_tax(c_tax, tax_type="consumption")
                            
                            import_leak = base_p_fast * 0.05
                            restaurant.capital -= import_leak
                            engine.trade_balance -= import_leak
                            engine.tick_import_leakage += import_leak
                            engine._gov_spend(subsidy_amount)
                            engine.tick_subsidy_outflow += subsidy_amount
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
                fixed_subsidy = min(engine.healthcare_subsidy_fixed, base_fee)
                fee = base_fee - fixed_subsidy
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
                            if not getattr(hospital, "is_informal", False):
                                c_tax = base_fee * engine.policies.get("consumption_tax", 0.0)
                                hospital.capital -= c_tax
                                engine.receive_tax(c_tax, tax_type="consumption")
                            
                            import_leak = base_fee * 0.05
                            hospital.capital -= import_leak
                            engine.trade_balance -= import_leak
                            engine.tick_import_leakage += import_leak
                            engine._gov_spend(subsidy_amount)
                            engine.tick_subsidy_outflow += subsidy_amount
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
            engine.tick_citizen_debt_interest += interest
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
        subsidy_g = min(engine.grocery_subsidy_fixed, base_p_grocery)
        p_grocery = base_p_grocery - subsidy_g

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
            if not getattr(store, "is_informal", False):
                c_tax = base_price * engine.policies.get("consumption_tax", 0.0)
                store.capital -= c_tax
                engine.receive_tax(c_tax, tax_type="consumption")
                
            import_leak = base_price * 0.05
            store.capital -= import_leak
            engine.trade_balance -= import_leak
            engine.tick_import_leakage += import_leak
            engine._gov_spend(subsidy_amount)
            engine.tick_subsidy_outflow += subsidy_amount

    def _buy_fast_food(self, rest: Optional["EnvironmentNode"], price: float, base_price: float, subsidy_amount: float, engine: "SimulationEngine", deduct_balance: bool = True) -> None:
        if deduct_balance:
            self.bank_balance -= price
        self.total_spending += price
        self.energy = min(2458.0, self.energy + 1966.4)
        self.health = max(0.0, self.health - 12.0)
        self.stress_level = min(100.0, self.stress_level + 5.0)
        if rest:
            rest.receive_revenue(base_price, self)
            if not getattr(rest, "is_informal", False):
                c_tax = base_price * engine.policies.get("consumption_tax", 0.0)
                rest.capital -= c_tax
                engine.receive_tax(c_tax, tax_type="consumption")
            
            import_leak = base_price * 0.05
            rest.capital -= import_leak
            engine.trade_balance -= import_leak
            engine.tick_import_leakage += import_leak
            engine._gov_spend(subsidy_amount)
            engine.tick_subsidy_outflow += subsidy_amount

    def _seek_healthcare(self, engine: "SimulationEngine") -> None:
        hospital = engine.get_best_available_node("Hospital", self)
        if not hospital: return

        base_fee = hospital.price * 3.0
        fixed_subsidy = min(engine.healthcare_subsidy_fixed, base_fee)
        fee = base_fee - fixed_subsidy
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
            if not getattr(hospital, "is_informal", False):
                c_tax = base_fee * engine.policies.get("consumption_tax", 0.0)
                hospital.capital -= c_tax
                engine.receive_tax(c_tax, tax_type="consumption")
                
            import_leak = base_fee * 0.05
            hospital.capital -= import_leak
            engine.trade_balance -= import_leak
            engine.tick_import_leakage += import_leak
            engine._gov_spend(subsidy_amount)
            engine.tick_subsidy_outflow += subsidy_amount
        else:
            self.health = max(0.0, self.health - 10.0)

    def _search_for_job(self, engine: "SimulationEngine") -> None:
        available_workplaces = engine.get_nodes_with_job_openings(self)
        if not available_workplaces: 
            self.months_unemployed += 1
            return

        best_wp = max(available_workplaces, key=lambda wp: wp.calculate_wage(self), default=None)
        if best_wp and best_wp.hire_employee(self):
            self.is_employed = True
            self.employer_id = best_wp.node_id
            self.months_unemployed = 0
            engine.unregister_unemployed(self)
        else:
            self.months_unemployed += 1

    def receive_wage(self, amount: float) -> None:
        self.bank_balance += amount
        self.daily_earnings += amount
        self.total_earnings += amount
        self.work_experience += 1
        self.last_monthly_income = amount

    def lose_job(self, engine: "SimulationEngine") -> None:
        """Citizen loses job and enters unemployed pool."""
        self.is_employed = False
        self.employer_id = None
        self.months_unemployed = 0
        def prospect_value(v: float, lambda_: float = 2.25) -> float:
            return v if v >= 0 else lambda_ * v
        self.stress_level = min(100.0, self.stress_level + prospect_value(-20.0, lambda_=1.5))
        if engine and not self.is_dead and 18.0 <= self.age < 65.0 and not self.is_student:
            engine.register_unemployed(self)

    def die(self, cause: str, engine: Optional["SimulationEngine"] = None) -> None:
        self.is_dead = True
        self.cause_of_death = cause
        self.health = 0.0
        if engine:
            engine.unregister_unemployed(self)

    def __repr__(self) -> str:
        return f"Citizen({self.citizen_id}, Age={self.age:.1f}, SEIR={self.seir_state})"
