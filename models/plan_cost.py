from dataclasses import dataclass
from enum import Enum
from typing import ClassVar


@dataclass(frozen=True)
class PlanCostDetails:
    fixed_cost: float
    web_incident_cost: float
    mobile_incident_cost: float
    email_incident_cost: float


class PlanCost(Enum):
    EMPRENDEDOR: ClassVar[PlanCostDetails] = PlanCostDetails(
        fixed_cost=5.0, web_incident_cost=0.15, mobile_incident_cost=0.10, email_incident_cost=0.08
    )
    EMPRESARIO: ClassVar[PlanCostDetails] = PlanCostDetails(
        fixed_cost=6.0, web_incident_cost=0.13, mobile_incident_cost=0.08, email_incident_cost=0.06
    )
    EMPRESARIO_PLUS: ClassVar[PlanCostDetails] = PlanCostDetails(
        fixed_cost=8.0, web_incident_cost=0.10, mobile_incident_cost=0.06, email_incident_cost=0.04
    )

    @classmethod
    def get_costs(cls, plan_name: str) -> PlanCostDetails:
        try:
            return cls[plan_name.upper()].value
        except KeyError as err:
            raise ValueError(f'Invalid plan name: {plan_name}') from err
