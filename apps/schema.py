from typing import Any, Dict, List

from pydantic import BaseModel, Field


class AgentCard(BaseModel):
    name: str
    version: str
    description: str
    capabilities: List[str]
    endpoints: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)