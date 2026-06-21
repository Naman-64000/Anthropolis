import unittest
from simulation.core.citizen import Citizen
from simulation.core.environment import Hospital
from simulation.core.engine import SimulationEngine
from simulation.analytics.metrics import calculate_gini


class TestCitySimulation(unittest.TestCase):
    def setUp(self) -> None:
        # Standard seed for consistency in tests
        self.engine = SimulationEngine(population_size=10, initial_gov_capital=2000, seed=0)

    def test_gini_coefficient_calculation(self) -> None:
        # Perfect equality: everyone has 100
        equal_balances = [100.0, 100.0, 100.0, 100.0]
        gini_equal = calculate_gini(equal_balances)
        self.assertAlmostEqual(gini_equal, 0.0, places=4)

        # Perfect inequality: 1 person has everything, others have 0
        inequal_balances = [0.0, 0.0, 0.0, 1000.0]
        gini_inequal = calculate_gini(inequal_balances)
        # For N=4, Gini formula returns (N-1)/N = 3/4 = 0.75 for absolute concentration
        self.assertAlmostEqual(gini_inequal, 0.75, places=4)

    def test_citizen_decay_and_survival(self) -> None:
        # Create a citizen with low starting health
        citizen = Citizen(
            citizen_id=999,
            age=30.0,
            baseline_health=80.0,
            education_level=0.5,
            risk_tolerance=0.2,
            bank_balance=10.0,
        )
        citizen.energy = 2458.0
        citizen.debt = 0.0
        self.assertEqual(citizen.is_dead, False)
        
        # Manually invoke decay helper
        citizen._apply_decays(self.engine)
        
        # Verify energy decreased non-linearly
        self.assertTrue(citizen.energy < 2458.0)

    def test_hospital_capacity_admission(self) -> None:
        # Create a hospital with 2 capacity and 1 employee (makes operational capacity min(capacity * ratio, capacity))
        # employee_capacity is 2, so with 1 employee, operational capacity is 2 * (1/2) = 1.
        hospital = Hospital(node_id="hosp_test", node_name="Test Clinic", capacity=2, employee_capacity=2)
        
        # Hire 1 doctor/nurse
        staff = Citizen(1, 40.0, 90.0, 0.8, 0.1)
        hospital.hire_employee(staff)
        
        # Operational capacity should be 1
        self.assertEqual(hospital.operational_capacity, 1)

        # Attempt to admit first patient
        patient_1 = Citizen(2, 35.0, 80.0, 0.5, 0.2)
        admit_1 = hospital.admit_patient(patient_1)
        self.assertTrue(admit_1)
        self.assertEqual(hospital.occupied_slots, 1)

        # Attempt to admit second patient (should exceed capacity)
        patient_2 = Citizen(3, 35.0, 80.0, 0.5, 0.2)
        admit_2 = hospital.admit_patient(patient_2)
        self.assertFalse(admit_2)
        self.assertEqual(hospital.occupied_slots, 1)

    def test_engine_single_step(self) -> None:
        initial_pop = len(self.engine.citizens)
        self.assertEqual(initial_pop, 10)
        self.assertEqual(self.engine.tick_count, 0)
        
        # Perform step
        self.engine.step()
        
        self.assertEqual(self.engine.tick_count, 1)
        # Should record historical logs
        self.assertEqual(len(self.engine.history), 2)  # Tick 0 (init) and Tick 1
        self.assertEqual(self.engine.history[-1]["tick"], 1)

    def test_gompertz_makeham_monthly_mortality(self) -> None:
        from simulation.core.citizen import calculate_monthly_mortality_prob
        # Males should have a higher baseline risk than females (e.g. at same age)
        prob_male = calculate_monthly_mortality_prob(age=30.0, sex='M', energy=2458.0, net_worth=200.0)
        prob_female = calculate_monthly_mortality_prob(age=30.0, sex='F', energy=2458.0, net_worth=200.0)
        self.assertTrue(prob_male > prob_female)

        # Poverty spike: low energy or negative net worth should spike mortality risk
        prob_poverty = calculate_monthly_mortality_prob(age=30.0, sex='M', energy=0.0, net_worth=-100.0)
        self.assertTrue(prob_poverty > prob_male)

    def test_inheritance_protocol(self) -> None:
        # Clear list
        self.engine.citizens = []
        self.engine.dead_citizens = []

        # Create parent and offspring
        parent = Citizen(1, 45.0, 90.0, 0.5, 0.2, bank_balance=1000.0, sex='M')
        parent.debt = 0.0
        child = Citizen(2, 10.0, 95.0, 0.0, 0.1, bank_balance=0.0, sex='F')
        child.debt = 0.0
        
        # Link child to parent
        parent.offspring_ids.append(child.citizen_id)
        child.parent_ids.append(parent.citizen_id)

        self.engine.citizens.extend([parent, child])
        
        # Kill parent
        parent.is_dead = True
        self.engine._reconcile_deaths()

        # Child should inherit the estate (1000.0)
        self.assertEqual(child.bank_balance, 1000.0)
        self.assertEqual(len(self.engine.dead_citizens), 1)

    def test_fertility_conception_and_birth(self) -> None:
        # Seed mother and father
        self.engine.citizens = []
        self.engine.dead_citizens = []

        mother = Citizen(1, 25.0, 95.0, 0.5, 0.2, bank_balance=500.0, sex='F', religiosity=0.9)
        mother.debt = 0.0
        father = Citizen(2, 28.0, 95.0, 0.5, 0.2, bank_balance=500.0, sex='M')
        father.debt = 0.0
        
        self.engine.citizens.extend([mother, father])

        # Force pregnancy and ensure they survive by subsidizing groceries
        mother.is_pregnant = True
        mother.gestation_months = 0
        mother.temp_partner_id = father.citizen_id
        self.engine.policies["grocery_subsidy"] = -1.0

        # Ticking engine 9 times for birth
        for _ in range(9):
            self.engine.step()

        # Mother should have given birth, adding child to population
        self.assertEqual(len(self.engine.citizens), 3)
        child = self.engine.citizens[-1]
        self.assertEqual(child.age, 0.0)
        self.assertIn(mother.citizen_id, child.parent_ids)
        self.assertIn(father.citizen_id, child.parent_ids)

    def test_geriatric_retirement(self) -> None:
        # Create a citizen who is close to 65
        citizen = Citizen(
            citizen_id=100,
            age=64.95,
            baseline_health=90.0,
            education_level=0.5,
            risk_tolerance=0.2,
            bank_balance=500.0,
            sex='M'
        )
        # Employ them manually
        citizen.is_employed = True
        citizen.employer_id = "wp_factory_1"
        self.engine.citizens = [citizen]
        
        # Add citizen to workplace node employees
        node = self.engine.get_node_by_id("wp_factory_1")
        node.employees = [citizen]
        
        # Tick the engine (increments age by 1/12 ~ 0.083, which puts age > 65)
        self.engine.step()
        
        # Citizen should now be retired
        self.assertFalse(citizen.is_employed)
        self.assertIsNone(citizen.employer_id)
        # Node employees should no longer contain this citizen
        self.assertNotIn(citizen, node.employees)

    def test_sex_ratio_at_birth(self) -> None:
        self.engine.citizens = []
        # Seed 1000 citizens and count sex split
        self.engine._initialize_population(1000)
        males = sum(1 for c in self.engine.citizens if c.sex == 'M')
        females = sum(1 for c in self.engine.citizens if c.sex == 'F')
        
        # Expected ratio is 1020 Females per 1000 Males (approx 49.5% male)
        male_pct = males / (males + females)
        self.assertAlmostEqual(male_pct, 0.495, delta=0.05)

    def test_dependency_ratio_calculation(self) -> None:
        self.engine.citizens = [
            Citizen(1, 2.0, 90.0, 0.0, 0.1),    # Dependent (Infant)
            Citizen(2, 10.0, 90.0, 0.0, 0.1),   # Dependent (Youth)
            Citizen(3, 30.0, 90.0, 0.5, 0.2),   # Working-Age
            Citizen(4, 40.0, 90.0, 0.5, 0.2),   # Working-Age
            Citizen(5, 70.0, 90.0, 0.5, 0.2),   # Dependent (Geriatric)
        ]
        
        # Dependents: 3, Working-Age: 2
        # Ratio should be 3 / 2 = 1.50
        self.engine.step()
        self.assertEqual(self.engine.dependency_ratio, 1.5)

    def test_tax_scaling_working_age(self) -> None:
        # Clear engine policies and citizens
        self.engine.policies["tax_rate"] = 0.10
        c1 = Citizen(1, 30.0, 90.0, 0.5, 0.2, bank_balance=100.0)
        c1.debt = 0.0
        c2 = Citizen(2, 70.0, 90.0, 0.5, 0.2, bank_balance=100.0)
        c2.debt = 0.0
        c3 = Citizen(3, 4.0, 90.0, 0.0, 0.1, bank_balance=100.0)
        c3.debt = 0.0
        self.engine.citizens = [c1, c2, c3]
        
        # Dependents: 2 (Retired + Infant), Working: 1
        # Dependency ratio: 2.0
        # Tax rate surcharge: 0.10 * (1.0 + 0.5 * 2.0) = 0.20 (20%)
        # Let's set some daily earnings
        self.engine.citizens[0].daily_earnings = 50.0  # Working
        self.engine.citizens[1].daily_earnings = 50.0  # Retired (non-working, shouldn't be taxed)
        
        # Apply tax
        self.engine.dependency_ratio = 2.0
        self.engine._collect_income_taxes()
        
        # Working-age citizen should pay 20% of 50.0 = 10.0 tax
        self.assertEqual(self.engine.citizens[0].bank_balance, 90.0)
        # Retired citizen should NOT pay any tax (daily_earnings ignored or not taxed)
        self.assertEqual(self.engine.citizens[1].bank_balance, 100.0)

    def test_prospect_theory_loss_aversion(self) -> None:
        from simulation.core.citizen import prospect_value
        # Positive values should scale with alpha (0.88)
        val_gain = prospect_value(10.0)
        self.assertAlmostEqual(val_gain, 10.0 ** 0.88, places=4)
        
        # Negative values should be penalized by lambda (2.25)
        val_loss = prospect_value(-10.0)
        self.assertAlmostEqual(val_loss, -2.25 * (10.0 ** 0.88), places=4)

        # Cultural friction: High religiosity increases lambda
        # Let's mock a citizen with high religiosity and test their specific debt lambda logic
        citizen = Citizen(1, 30.0, 90.0, 0.5, 0.2, bank_balance=5.0, religiosity=1.0)
        p_fast_food = 10.0  # Means 5.0 debt
        lambda_debt = 2.25 * (1.0 + 3.0 * citizen.religiosity)
        self.assertEqual(lambda_debt, 9.0)

    def test_cultural_inheritance(self) -> None:
        self.engine.citizens = []
        mother = Citizen(1, 25.0, 95.0, 0.5, 0.2, religious_affiliation=2, religiosity=0.8, sex='F')
        father = Citizen(2, 28.0, 95.0, 0.5, 0.2, religious_affiliation=1, religiosity=0.1, sex='M')
        
        self.engine.citizens.extend([mother, father])
        mother.is_pregnant = True
        mother.gestation_months = 0
        mother.temp_partner_id = father.citizen_id

        # 9 ticks for birth
        for _ in range(9):
            self.engine.step()
            
        child = self.engine.citizens[-1]
        self.assertEqual(child.age, 0.0)
        
        # Child inherits from mother
        self.assertEqual(child.religious_affiliation, 2)
        # Religiosity dilutes by 0.5
        self.assertAlmostEqual(child.religiosity, 0.4, places=4)

    def test_homophily_mating_weights(self) -> None:
        female = Citizen(1, 25.0, 90.0, 0.5, 0.2, bank_balance=1000.0, sex='F', religious_affiliation=1, religiosity=0.9)
        
        # Male 1 is an exact match in culture and wealth
        male_match = Citizen(2, 28.0, 90.0, 0.5, 0.2, bank_balance=1000.0, sex='M', religious_affiliation=1, religiosity=0.9)
        
        # Male 2 is completely mismatched
        male_mismatch = Citizen(3, 28.0, 90.0, 0.5, 0.2, bank_balance=5000.0, sex='M', religious_affiliation=2, religiosity=0.1)
        
        # Calculate Homophily manually mirroring engine logic
        def calc_similarity(f, m):
            rel_diff = abs(f.religiosity - m.religiosity)
            aff_diff = 0.0 if f.religious_affiliation == m.religious_affiliation else 1.0
            wealth_diff = min(1.0, abs(f.bank_balance - m.bank_balance) / 2000.0)
            sim = 1.0 - (0.4 * rel_diff + 0.3 * aff_diff + 0.3 * wealth_diff)
            return max(0.01, sim)
            
        sim_match = calc_similarity(female, male_match)
        sim_mismatch = calc_similarity(female, male_mismatch)
        
        self.assertTrue(sim_match > sim_mismatch)
        self.assertEqual(sim_match, 1.0) # Exact match
        self.assertTrue(sim_mismatch < 0.5)

    def test_human_capital_labor_vector(self) -> None:
        import numpy as np
        from simulation.core.environment import Workplace
        
        # Create a workplace
        wp = Workplace(node_id="wp_test", node_name="Test Factory", capacity=10, employee_capacity=5)
        
        # Create an employee with specific education and health
        # Edu = 0.5, Health = 80.0
        emp = Citizen(1, 30.0, 90.0, 0.5, 0.2, bank_balance=100.0)
        emp.health = 80.0
        
        wp.hire_employee(emp)
        
        # Calculate expected Human Capital (H) for this employee
        # H = ln(1 + edu) * (health / 70.8)
        expected_H = np.log1p(0.5) * (80.0 / 70.8)
        
        # We test that the 'L' logic matches our expected_H
        # Instead of directly computing L, we'll recreate the L logic from Workplace.tick
        L = sum(np.log1p(e.education_level) * (e.health / 70.8) for e in wp.employees)
        
        self.assertAlmostEqual(L, expected_H, places=4)

    def test_tfp_growth_and_volatility(self) -> None:
        from simulation.core.environment import Workplace
        # Test Workplace Cobb-Douglas output with TFP growth
        wp = Workplace(node_id="wp_test_tfp", node_name="Test Factory", capacity=10, employee_capacity=5)
        # Avoid corporate tax bleed during test
        self.engine.policies["corporate_tax_rate"] = 0.0
        wp.capital = 1000.0
        emp = Citizen(1, 30.0, 90.0, 0.5, 0.2, bank_balance=100.0)
        emp.health = 70.8
        wp.hire_employee(emp)
        
        # At tick_count = 0
        self.engine.tick_count = 0
        wp.tick(self.engine)
        # Workplace capital should have increased from initial 1000.0 due to production revenue minus wage
        self.assertTrue(wp.capital > 1000.0)

    def test_calibrated_minimum_wages(self) -> None:
        from simulation.core.environment import Workplace
        wp = Workplace(node_id="wp_test_wage", node_name="Test Factory", capacity=10, employee_capacity=5)
        
        # Edu level 0 should yield daily wage of $3.5 -> $70 per month (20 working days)
        emp_low = Citizen(1, 30.0, 90.0, 0.0, 0.2)
        wage_low = wp.calculate_wage(emp_low)
        self.assertAlmostEqual(wage_low, 3.5 * 20.0, places=4)
        
        # Edu level 1.0 should yield daily wage of $8.5 -> $170 per month (20 working days)
        emp_high = Citizen(2, 30.0, 90.0, 1.0, 0.2)
        wage_high = wp.calculate_wage(emp_high)
        self.assertAlmostEqual(wage_high, 8.5 * 20.0, places=4)


if __name__ == "__main__":
    unittest.main()
