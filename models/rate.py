from dataclasses import dataclass

from .plan import Plan


@dataclass
class Rate:
    id: str
    plan: Plan
    client_id: str
    fixed_cost: float
    cost_per_incident_web: float
    cost_per_incident_mobile: float
    cost_per_incident_email: float
