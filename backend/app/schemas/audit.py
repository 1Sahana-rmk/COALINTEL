from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: int
    user: str
    action: str
    details: str
    ip: str
    timestamp: str

    model_config = ConfigDict(from_attributes=True)
