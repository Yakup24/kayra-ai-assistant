from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import uuid4


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    user_role: Optional[str] = Field(default="general", max_length=40)
    online_enabled: bool = False


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


class PlatformMetric(BaseModel):
    label: str
    value: str
    trend: str


class Capability(BaseModel):
    title: str
    description: str
    status: str


class IntegrationStatus(BaseModel):
    name: str
    category: str
    status: str
    description: str


class SecurityControl(BaseModel):
    title: str
    level: str
    description: str


class RoadmapItem(BaseModel):
    phase: str
    title: str
    status: str
    owner: str


class AuditEvent(BaseModel):
    created_at: str
    event_type: str
    summary: str
    risk_level: str


class EnterpriseOverviewResponse(BaseModel):
    product_name: str
    tagline: str
    maturity: str
    metrics: List[PlatformMetric]
    capabilities: List[Capability]
    integrations: List[IntegrationStatus]
    security_controls: List[SecurityControl]
    roadmap: List[RoadmapItem]


class AuditTrailResponse(BaseModel):
    events: List[AuditEvent]


class KnowledgeDocumentRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    content: str = Field(..., min_length=20, max_length=12000)
    category: str = Field(default="Kurumsal", max_length=60)


class KnowledgeDocumentResponse(BaseModel):
    status: str
    path: str
    indexed_chunks: int


class KnowledgeDocumentInfo(BaseModel):
    filename: str
    title: str
    category: str
    size: int
    updated_at: str


class KnowledgeDocumentListResponse(BaseModel):
    documents: List[KnowledgeDocumentInfo]


class TicketDraftRequest(BaseModel):
    message: str = Field(..., min_length=3, max_length=2000)
    priority: str = Field(default="normal", max_length=30)
    requester: Optional[str] = Field(default=None, max_length=120)


class TicketDraftResponse(BaseModel):
    title: str
    priority: str
    category: str
    summary: str
    acceptance_criteria: List[str]
    escalation_required: bool


class TicketCreateRequest(BaseModel):
    message: str = Field(..., min_length=3, max_length=2000)
    priority: str = Field(default="normal", max_length=30)
    requester: Optional[str] = Field(default=None, max_length=120)


class TicketRecord(BaseModel):
    id: str
    title: str
    priority: str
    category: str
    summary: str
    status: str
    requester: str
    assignee: Optional[str] = None
    resolution_note: Optional[str] = None
    sla_minutes: int
    sla_due_at: str
    sla_status: str
    resolved_at: Optional[str] = None
    resolution_minutes: Optional[int] = None
    resolution_score: Optional[int] = None
    escalation_required: bool
    created_at: str
    updated_at: str


class TicketListResponse(BaseModel):
    tickets: List[TicketRecord]


class TicketUpdateRequest(BaseModel):
    status: Optional[str] = Field(default=None, max_length=30)
    assignee: Optional[str] = Field(default=None, max_length=120)
    priority: Optional[str] = Field(default=None, max_length=30)
    resolution_note: Optional[str] = Field(default=None, max_length=1000)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=80)
    password: str = Field(..., min_length=1, max_length=120)


class UserProfile(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    display_name: str
    role: str
    active: bool = True


class AuthResponse(BaseModel):
    token: str
    user: UserProfile


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=40)
    email: Optional[str] = Field(default=None, max_length=120)
    password: str = Field(..., min_length=6, max_length=120)
    display_name: Optional[str] = Field(default=None, max_length=80)
    role: str = Field(default="employee", max_length=30)


class UserListResponse(BaseModel):
    users: List[UserProfile]


class PasswordResetRequest(BaseModel):
    password: str = Field(..., min_length=6, max_length=120)


class UserStatusRequest(BaseModel):
    active: bool


class IntegrationConfig(BaseModel):
    id: str
    name: str
    category: str
    status: str
    enabled: bool
    endpoint: Optional[str] = None
    description: str
    updated_at: str


class IntegrationListResponse(BaseModel):
    integrations: List[IntegrationConfig]


class IntegrationUpdateRequest(BaseModel):
    status: Optional[str] = Field(default=None, max_length=40)
    enabled: Optional[bool] = None
    endpoint: Optional[str] = Field(default=None, max_length=240)


class ConversationMessage(BaseModel):
    role: str
    content: str
    created_at: str
    domain: Optional[str] = None
    confidence: Optional[float] = None


class ConversationHistoryResponse(BaseModel):
    session_id: str
    messages: List[ConversationMessage]
