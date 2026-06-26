import unittest
import os
import json
from simulation.core.engine import SimulationEngine

class TestSerialization(unittest.TestCase):
    def test_engine_serialization(self):
        engine = SimulationEngine(population_size=150, seed=42)
        engine.step()
        
        # Save to checkpoint
        test_file = "test_checkpoint.json"
        engine.save_checkpoint(test_file)
        
        self.assertTrue(os.path.exists(test_file))
        
        # Load from checkpoint
        engine_loaded = SimulationEngine.load_checkpoint(test_file)
        
        # Compare a few properties
        self.assertEqual(engine.tick_count, engine_loaded.tick_count)
        self.assertEqual(engine.government_capital, engine_loaded.government_capital)
        self.assertEqual(engine.next_citizen_id, engine_loaded.next_citizen_id)
        self.assertEqual(len(engine.citizens), len(engine_loaded.citizens))
        self.assertEqual(len(engine.nodes), len(engine_loaded.nodes))
        
        # Compare a citizen
        c1 = engine.citizens[0]
        c2 = engine_loaded.citizens[0]
        self.assertEqual(c1.citizen_id, c2.citizen_id)
        self.assertEqual(c1.bank_balance, c2.bank_balance)
        self.assertEqual(c1.health, c2.health)
        
        # Compare a node
        n1 = engine.nodes[0]
        n2 = engine_loaded.nodes[0]
        self.assertEqual(n1.node_id, n2.node_id)
        self.assertEqual(n1.capital, n2.capital)
        self.assertEqual(len(n1.employees), len(n2.employees))
        
        # Run the original engine to get expected results
        engine.step()
        expected_tick = engine.tick_count
        expected_capital = engine.government_capital
        expected_tax = engine.tick_tax_inflow
        
        # Now reload the checkpoint, which restores the global random state to exactly what it was BEFORE engine.step() ran
        engine_loaded = SimulationEngine.load_checkpoint(test_file)
        
        # Step the loaded engine
        engine_loaded.step()
        
        # They should now perfectly match, because engine_loaded got the exact same random numbers
        self.assertEqual(expected_tick, engine_loaded.tick_count)
        self.assertAlmostEqual(expected_capital, engine_loaded.government_capital, places=2)
        self.assertAlmostEqual(expected_tax, engine_loaded.tick_tax_inflow, places=2)
        
        os.remove(test_file)

if __name__ == '__main__':
    unittest.main()
