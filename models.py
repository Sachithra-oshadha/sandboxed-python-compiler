from pydantic import BaseModel
from enum import Enum
from datetime import datetime

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class CodeSubmission(BaseModel):
    code: str
    timeout: int = 10  # seconds

class ExecutionResult(BaseModel):
    execution_id: str
    status: ExecutionStatus
    output: str = ""
    error: str = ""
    start_time: datetime | None = None
    execution_time: float | None = None
    lines_of_code: int = 0