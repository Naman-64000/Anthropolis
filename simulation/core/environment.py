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
        location: str = "Urban",
        is_informal: bool = False,
    ) -> None:
        self.node_id: str = node_id
        self.node_name: str = node_name
        self.node_type: str = node_type
        self.capacity: int = capacity
        self.price: float = price
        self.employee_capacity: int = employee_capacity
        self.capital: float = base_capital
        
        self.location: str = location
        self.is_informal: bool = is_informal

        self.employees: List["Citizen"] = []
        self.occupied_slots: int = 0
        self.monthly_revenue: float = 0.0
        self.monthly_wages: float = 0.0
        self.monthly_dividends: float = 0.0
        self.revenue_history: List[float] = []
        # Set True by engine when a government bailout was issued this tick;
        # allows skeleton-crew hiring to bypass the revenue-history gate.
        self.received_bailout_this_tick: bool = False

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "node_type": self.node_type,
            "capacity": self.capacity,
            "price": self.price,
            "employee_capacity": self.employee_capacity,
            "capital": self.capital,
            "location": self.location,
            "is_informal": self.is_informal,
            "employee_ids": [emp.citizen_id for emp in self.employees],
            "occupied_slots": self.occupied_slots,
            "monthly_revenue": self.monthly_revenue,
            "monthly_wages": self.monthly_wages,
            "monthly_dividends": self.monthly_dividends,
            "revenue_history": self.revenue_history,
            "received_bailout_this_tick": self.received_bailout_this_tick,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EnvironmentNode":
        # Note: subclasses have different initializers, but they don't override 
        # base properties other than the constructor args. 
        node_type = data["node_type"]
        
        if node_type == "Workplace":
            node = Workplace(data["node_id"], data["node_name"], data["capacity"], data["employee_capacity"])
        elif node_type == "Hospital":
            node = Hospital(data["node_id"], data["node_name"], data["capacity"], data["employee_capacity"])
        elif node_type == "School":
            node = School(data["node_id"], data["node_name"], data["capacity"], data["employee_capacity"])
        elif node_type == "GroceryStore":
            node = GroceryStore(data["node_id"], data["node_name"], data["capacity"], data["employee_capacity"])
        elif node_type == "Restaurant":
            node = Restaurant(data["node_id"], data["node_name"], data["capacity"], data["employee_capacity"])
        else:
            node = EnvironmentNode(
                node_id=data["node_id"],
                node_name=data["node_name"],
                node_type=data["node_type"],
                capacity=data["capacity"],
                price=data["price"],
                employee_capacity=data["employee_capacity"],
                base_capital=data["capital"],
                location=data.get("location", "Urban"),
                is_informal=data.get("is_informal", False)
            )
            
        node.price = data["price"]
        node.capital = data["capital"]
        node.location = data.get("location", "Urban")
        node.is_informal = data.get("is_informal", False)
        # employee_ids will be linked into actual Citizen objects by the SimulationEngine
        node._pending_employee_ids = data["employee_ids"]
        node.occupied_slots = data["occupied_slots"]
        node.monthly_revenue = data["monthly_revenue"]
        node.monthly_wages = data["monthly_wages"]
        node.monthly_dividends = data["monthly_dividends"]
        node.revenue_history = data["revenue_history"]
        node.received_bailout_this_tick = data["received_bailout_this_tick"]
        return node

    @property
    def operational_capacity(self) -> int:
        if not self.employees: return 0
        return int(self.capacity * (len(self.employees) / self.employee_capacity))

    def tick(self, engine: "SimulationEngine") -> None:
        # Reset per-tick bailout flag from any previous tick.
        # NOTE: occupied_slots is NOT reset here. The engine resets it at the
        # start of each step(), before citizen.tick() runs, so that admissions
        # made during citizen.tick() are still readable by _record_metrics().
        self.received_bailout_this_tick = False

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
                emp.lose_job(engine)
                continue
                
            wage = self.calculate_wage(emp)
            if self.capital >= wage:
                self.capital -= wage
                self.monthly_wages += wage
                emp.receive_wage(wage)
            else:
                to_fire.append(emp)
                emp.lose_job(engine)

        for emp in to_fire:
            if emp in self.employees:
                self.employees.remove(emp)

        self.pay_taxes(engine)

        if self.capital > 500.0 and len(self.employees) < self.employee_capacity:
            self._attempt_hiring(engine)
            
        self.revenue_history.append(self.monthly_revenue)
        if len(self.revenue_history) > 5:
            self.revenue_history.pop(0)

        self.monthly_revenue = 0.0
        self.monthly_dividends = 0.0

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

    def calculate_wage(self, emp: "Citizen") -> float:
        # Daily wage ranges from $3.5 to $8.5 based on education/skill (₹300 to ₹700)
        base_wage = 3.5 + emp.education_level * 5.0
        
        # Structural Caste Inequality Penalty/Bonus
        if getattr(emp, "caste", "General") == "General":
            caste_multiplier = 1.15
        elif getattr(emp, "caste", "General") == "OBC":
            caste_multiplier = 0.95
        elif getattr(emp, "caste", "General") == "SC":
            caste_multiplier = 0.85
        else: # ST
            caste_multiplier = 0.75
            
        # Religious Stratification / Network Effects
        rel = getattr(emp, "religious_affiliation", 0)
        if rel in (1, 4):  # Muslim, Other
            religion_multiplier = 0.90
        elif rel in (2, 3): # Christian, Sikh
            religion_multiplier = 1.05
        else: # Hindu
            religion_multiplier = 1.0
            
        base_wage *= (caste_multiplier * religion_multiplier)
        
        # Performance/Health modifier inflation (price level) relative to initial price of 5.0
        price_factor = (self.price / 5.0) if self.node_type == "Workplace" else 1.0
        return base_wage * 20.0 * price_factor

    # Skeleton crew size: minimum staff a bailed-out public node can hire
    # to restart revenue generation before revenue_history is populated.
    SKELETON_CREW_SIZE: int = 2

    def hire_employee(self, citizen: "Citizen") -> bool:
        if len(self.employees) >= self.employee_capacity:
            return False

        projected_wages = sum(self.calculate_wage(e) for e in self.employees)
        new_wage = self.calculate_wage(citizen)

        # --- Recovery path: freshly bailed-out public nodes ---
        # A Hospital or School that just received a government bailout has
        # no revenue_history yet but needs a skeleton crew to begin admitting
        # patients / students and generating revenue. Allow hiring up to
        # SKELETON_CREW_SIZE unconditionally (capital was just injected).
        is_public_node = self.node_type in ("Hospital", "School")
        if self.received_bailout_this_tick and is_public_node:
            if len(self.employees) < self.SKELETON_CREW_SIZE:
                self.employees.append(citizen)
                return True
            # Skeleton crew already at SKELETON_CREW_SIZE — block the normal
            # capital-based fallback below so the node doesn't overhire before
            # it has real revenue history. The revenue gate kicks in on future
            # ticks once revenue_history has accumulated >= 3 entries.
            return False

        # --- Normal revenue-based gate ---
        if len(self.revenue_history) >= 3:
            trailing_avg_revenue = sum(self.revenue_history) / len(self.revenue_history)
            if (trailing_avg_revenue - projected_wages - new_wage) > 0.0:
                self.employees.append(citizen)
                return True
        else:
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
        slots_available = self.employee_capacity - len(self.employees)
        if slots_available <= 0: return
        
        candidates_to_hire = []
        # engine.unemployed_candidates is sorted ascending by education_level,
        # so reversed() gives descending order (highest education first).
        for candidate in reversed(engine.unemployed_candidates):
            if slots_available <= 0:
                break
            if self.hire_employee(candidate):
                candidate.is_employed = True
                candidate.employer_id = self.node_id
                slots_available -= 1
                candidates_to_hire.append(candidate)
                
        for candidate in candidates_to_hire:
            engine.unregister_unemployed(candidate)


class Workplace(EnvironmentNode):
    def __init__(self, node_id: str, node_name: str, capacity: int, employee_capacity: int, **kwargs) -> None:
        super().__init__(node_id, node_name, "Workplace", capacity, price=5.0, employee_capacity=employee_capacity, **kwargs)

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
            
            alpha = engine.parameters.get("cobb_douglas_alpha", 0.42)
            beta = engine.parameters.get("cobb_douglas_beta", 0.58)
            output = calculate_cobb_douglas_output(A, K, L, alpha=alpha, beta=beta)
            # Economic Volatility: India VIX volatility (~14.5% annual std dev -> ~4.18% monthly)
            market_fluctuation = max(0.2, float(np.random.normal(1.0, 0.145 / np.sqrt(12.0))))
            gross_revenue = output * self.price * market_fluctuation
            
            # Trade & FDI Logic
            export_fraction = 0.20 # 20% exported
            export_revenue = gross_revenue * export_fraction
            
            import_fraction = 0.15 # 15% spent on imported raw materials
            import_costs = gross_revenue * import_fraction
            
            domestic_revenue = gross_revenue * (1.0 - export_fraction)
            
            # Record macro trade statistics on engine
            if not hasattr(engine, "trade_balance"):
                engine.trade_balance = 0.0
            engine.trade_balance += export_revenue
            engine.trade_balance -= import_costs
            
            if not hasattr(engine, "foreign_reserves"):
                engine.foreign_reserves = 0.0
            engine.foreign_reserves += export_revenue
            engine.foreign_reserves -= import_costs
            
            # Small random FDI injection (0.5% chance)
            if random.random() < 0.005:
                fdi_injection = float(np.random.lognormal(mean=5.0, sigma=1.0)) * 100.0
                self.capital += fdi_injection
                if not hasattr(engine, "fdi_inflow"):
                    engine.fdi_inflow = 0.0
                engine.fdi_inflow += fdi_injection
                engine.tick_fdi_inflow += fdi_injection
            
            engine.tick_economic_output += gross_revenue
            engine.tick_import_leakage += import_costs
            
            net_new_capital = (domestic_revenue + export_revenue) - import_costs
            self.monthly_revenue += (domestic_revenue + export_revenue)
            self.capital += net_new_capital

        super().tick(engine)

        # Profit Dividend Distribution
        # Excess capital beyond a healthy reserve (5.0x monthly wage bill) is partially
        # distributed as dividends to employed citizens based on their human capital.
        if self.employees:
            reserve_threshold = self.monthly_wages * 5.0
            if self.capital > reserve_threshold:
                excess_capital = self.capital - reserve_threshold
                dividend_pool = excess_capital * 0.10  # distribute 10% of excess
                
                # Compute human capital (H_i) for each employee
                # H_i = (0.1 + ln(1 + education_level)) * (health / 70.8)
                h_values = []
                for emp in self.employees:
                    h_i = (0.1 + np.log1p(emp.education_level)) * (emp.health / 70.8)
                    h_values.append((emp, h_i))
                
                total_h = sum(h for _, h in h_values)
                if total_h > 0.0:
                    for emp, h_i in h_values:
                        share = (h_i / total_h) * dividend_pool
                        emp.bank_balance += share
                        emp.last_dividend = share
                        emp.total_dividends_received += share
                        self.capital -= share
                        self.monthly_dividends += share


class Hospital(EnvironmentNode):
    def __init__(self, node_id: str, node_name: str, capacity: int, employee_capacity: int, **kwargs) -> None:
        super().__init__(node_id, node_name, "Hospital", capacity, price=133.33, employee_capacity=employee_capacity, **kwargs)

    def admit_patient(self, citizen: "Citizen") -> bool:
        if self.occupied_slots < self.operational_capacity:
            self.occupied_slots += 1
            return True
        return False


class School(EnvironmentNode):
    def __init__(self, node_id: str, node_name: str, capacity: int, employee_capacity: int, **kwargs) -> None:
        super().__init__(node_id, node_name, "School", capacity, price=3.25, employee_capacity=employee_capacity, **kwargs)


class GroceryStore(EnvironmentNode):
    def __init__(self, node_id: str, node_name: str, capacity: int, employee_capacity: int, **kwargs) -> None:
        super().__init__(node_id, node_name, "GroceryStore", capacity, price=1.50, employee_capacity=employee_capacity, **kwargs)


class Restaurant(EnvironmentNode):
    def __init__(self, node_id: str, node_name: str, capacity: int, employee_capacity: int, **kwargs) -> None:
        super().__init__(node_id, node_name, "Restaurant", capacity, price=1.50, employee_capacity=employee_capacity, **kwargs)
