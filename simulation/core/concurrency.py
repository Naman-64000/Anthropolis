import concurrent.futures
from typing import List, Dict, Any

class CitizenTickDelta:
    def __init__(self):
        self.tax_paid: float = 0.0
        self.subsidy_claimed: float = 0.0
        self.node_revenues: Dict[str, float] = {}
        self.consumption_tax_paid: float = 0.0
        self.job_search: bool = False
        self.hospital_admit: bool = False

    def add_node_revenue(self, node_id: str, amount: float):
        self.node_revenues[node_id] = self.node_revenues.get(node_id, 0.0) + amount
