from dataclasses import dataclass

from .channel import Channel
from .history_entry import HistoryEntry


@dataclass
class Incident:
    id: str
    name: str
    channel: Channel
    reported_by: str
    created_by: str
    assigned_to: str
    history: list[HistoryEntry]
