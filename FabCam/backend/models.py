from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class FileInfo(BaseModel):
    filename: str
    size: int
    created_at: str
    file_type: str  # 'video' or 'image'

class RecordingStatus(BaseModel):
    is_recording: bool
    start_time: Optional[str] = None
    duration: Optional[int] = None

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None