from dataclasses import dataclass
from datetime import datetime

from .action import Action


@dataclass
class HistoryEntry:
    seq: int
    date: datetime
    action: Action
    description: str
