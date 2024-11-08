from dataclasses import dataclass
from datetime import datetime

from models.month import Month


@dataclass
class Invoice:
    id: str
    client_id: str
    rate_id: str
    generation_date: datetime
    billing_month: Month
    billing_year: int
    payment_due_date: datetime
    total_incidents_web: int
    total_incidents_mobile: int
    total_incidents_email: int
