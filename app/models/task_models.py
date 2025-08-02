from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from datetime import datetime, timezone
from app.database.database import Base
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Union


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    weixin_user_id = Column(Integer, ForeignKey("weixin_users.id"), nullable=True)
    task_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default=TaskStatus.PENDING)
    progress = Column(Integer, nullable=False, default=0)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    params = Column(JSON, nullable=True)

    user = relationship("User", back_populates="tasks")
    weixin_user = relationship("WeixinUser", back_populates="tasks")

    def __init__(self, **kwargs):
        now = datetime.now(timezone.utc)
        kwargs.setdefault("created_at", now)
        kwargs.setdefault("updated_at", now)
        super().__init__(**kwargs)

    def update_status(self, status, progress=None, result=None, error=None):
        """Update task status and related fields"""
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
        
        if progress is not None:
            self.progress = progress
            
        if result is not None:
            self.result = result
            
        if error is not None:
            self.error = error


# Pydantic models for API
class TaskCreate(BaseModel):
    task_type: str
    params: Dict[str, Any]


class TaskResponse(BaseModel):
    id: int
    task_type: str
    status: TaskStatus
    progress: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TaskStatusResponse(BaseModel):
    id: int
    status: TaskStatus
    progress: int
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    class Config:
        from_attributes = True


class ProcessImageAsyncRequest(BaseModel):
    file_id: str
    analysis: Optional[Any] = None
    user_comment: Optional[str] = None 