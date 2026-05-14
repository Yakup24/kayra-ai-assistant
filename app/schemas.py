from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import uuid4


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    user_role: Optional[str] = Field(default="general", max_length=40)


class Source(BaseModel):
    title: str
    path: str
    score: float
    excerpt: str


class NextAction(BaseModel):
    label: str
    prompt: str


class ChatResponse(BaseModel):
    answer: str
    confidence: float
    sources: List[Source]
    follow_up_suggestions: List[str]
    next_actions: List[NextAction]
    handoff_recommended: bool
    intent: str
    domain: str
    risk_level: str
    response_time_ms: int
    session_id: str = Field(default_factory=lambda: str(uuid4()))


class FeedbackRequest(BaseModel):
    session_id: str
    message: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    status: str


class HealthResponse(BaseModel):
    status: str
    indexed_chunks: int
    app_name: str


class Topic(BaseModel):
    id: str
    title: str
    category: str
    prompt: str


class TopicsResponse(BaseModel):
    topics: List[Topic]
