from marshmallow_dataclass import dataclass


@dataclass
class Rate:
    id: str
    client_id: str
    fixed_cost: float
    cost_per_incident_web: float
    cost_per_incident_mobile: float
    cost_per_incident_email: float
