

from enum import Enum

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    travel_info_agent = "travel_info_agent"
    accommodation_booking_agent = "accommodation_booking_agent"

class AgentTypeOutput(BaseModel):
    agent: AgentType = Field(..., description="Which agent should handle the query?")