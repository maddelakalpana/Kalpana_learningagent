"""Simple session model for AI Learning Assistant."""
from dataclasses import dataclass, field
from typing import List


@dataclass
class LearningSession:
    session_id: str
    document_text: str = ""
    topic_name: str = ""
    mode: str = "teach"  # 'teach' or 'doubt'
    history: List[dict] = field(default_factory=list)
    status: str = "pending"
