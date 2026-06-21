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
