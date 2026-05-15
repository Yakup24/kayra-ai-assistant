from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.schemas import (
    AuditTrailResponse,
    AuthResponse,
    ChatRequest,
    ChatResponse,
    ConversationHistoryResponse,
    EnterpriseOverviewResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    IntegrationListResponse,
    IntegrationUpdateRequest,
    KnowledgeDocumentRequest,
    KnowledgeDocumentListResponse,
    KnowledgeDocumentResponse,
    LoginRequest,
    PasswordResetRequest,
    TicketDraftRequest,
    TicketDraftResponse,
    TicketCreateRequest,
    TicketListResponse,
    TicketRecord,
    TicketUpdateRequest,
    Topic,
    TopicsResponse,
    UserCreateRequest,
    UserListResponse,
    UserProfile,
    UserStatusRequest,
)
from app.services.analytics import AnalyticsLogger
from app.services.auth import AuthService
from app.services.conversation import ConversationStore
from app.services.enterprise import EnterpriseService
from app.services.online import OnlineSearchService
from app.services.ops import OpsService
from app.services.rag import KnowledgeBase
from app.services.response import ResponseGenerator


settings = get_settings()
knowledge_base = KnowledgeBase(settings.knowledge_dir)
response_generator = ResponseGenerator(knowledge_base, settings.min_confidence)
analytics = AnalyticsLogger(settings.log_dir)
enterprise = EnterpriseService(analytics, knowledge_base)
auth_service = AuthService(
    settings.log_dir / "kayra.sqlite3",
    settings.auth_secret,
    settings.admin_username,
    settings.admin_password,
    settings.support_username,
    settings.support_password,
)
conversation_store = ConversationStore(settings.log_dir / "conversations")
online_search = OnlineSearchService()
ops_service = OpsService(settings.log_dir / "ops.sqlite3", settings.knowledge_dir)

TOPICS = [
    Topic(id="returns", title="İade ve Kargo", category="Müşteri Destek", prompt="İade süreci nasıl işliyor?"),
    Topic(id="vpn", title="VPN ve Erişim", category="IT Destek", prompt="VPN bağlantı hatasında ne yapmalıyım?"),
    Topic(id="leave", title="Yıllık İzin", category="İK", prompt="Yıllık izin prosedürü nedir?"),
    Topic(id="privacy", title="KVKK ve Gizlilik", category="Uyumluluk", prompt="Kişisel veri paylaşmadan nasıl destek alabilirim?"),
    Topic(id="ops", title="SLA ve İzleme", category="Operasyon", prompt="Kurumsal chatbot için SLA ve izleme nasıl kurulmalı?"),
    Topic(id="architecture", title="Mimari Yol Haritası", category="Platform", prompt="Kayra Enterprise mimarisi nasıl ölçeklenmeli?"),
]

app = FastAPI(title=settings.app_name, version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


def current_user(authorization: str = Header(default="")) -> UserProfile:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Oturum gerekli.")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return auth_service.verify_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def admin_user(user: UserProfile = Depends(current_user)) -> UserProfile:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin yetkisi gerekli.")
    return user


def support_user(user: UserProfile = Depends(current_user)) -> UserProfile:
    if user.role not in {"admin", "support"}:
        raise HTTPException(status_code=403, detail="Destek uzmanı yetkisi gerekli.")
    return user


def should_use_online(message: str, online_enabled: bool) -> bool:
    lowered = message.lower()
    triggers = ["online", "internetten", "web", "güncel", "guncel", "son dakika", "araştır"]
    return online_enabled or any(trigger in lowered for trigger in triggers)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", indexed_chunks=len(knowledge_base.chunks), app_name=settings.app_name)


@app.get("/api/topics", response_model=TopicsResponse)
def topics() -> TopicsResponse:
    return TopicsResponse(topics=TOPICS)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(request: LoginRequest) -> AuthResponse:
    try:
        token, user = auth_service.login(request.username, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return AuthResponse(token=token, user=user)


@app.get("/api/auth/me", response_model=UserProfile)
def me(user: UserProfile = Depends(current_user)) -> UserProfile:
    return user


@app.get("/api/admin/users", response_model=UserListResponse)
def list_users(_: UserProfile = Depends(admin_user)) -> UserListResponse:
    return UserListResponse(users=auth_service.list_users())


@app.post("/api/admin/users", response_model=UserProfile)
def create_user(request: UserCreateRequest, admin: UserProfile = Depends(admin_user)) -> UserProfile:
    try:
        user = auth_service.create_user(
            username=request.username,
            password=request.password,
            email=request.email,
            display_name=request.display_name,
            role=request.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    analytics.log_chat(
        {
            "session_id": "admin",
            "message": f"user_created:{user.username}:{user.role}",
            "confidence": 1,
            "handoff_recommended": False,
            "source_count": 0,
            "domain": "Admin",
            "risk_level": "düşük",
            "response_time_ms": 1,
            "username": admin.username,
        }
    )
    return user


@app.post("/api/admin/users/{username}/password", response_model=UserProfile)
def reset_user_password(username: str, request: PasswordResetRequest, admin: UserProfile = Depends(admin_user)) -> UserProfile:
    try:
        user = auth_service.reset_password(username, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    analytics.log_chat(
        {
            "session_id": "admin",
            "message": f"user_password_reset:{username}",
            "confidence": 1,
            "handoff_recommended": False,
            "source_count": 0,
            "domain": "Admin",
            "risk_level": "orta",
            "response_time_ms": 1,
            "username": admin.username,
        }
    )
    return user


@app.patch("/api/admin/users/{username}/status", response_model=UserProfile)
def set_user_status(username: str, request: UserStatusRequest, admin: UserProfile = Depends(admin_user)) -> UserProfile:
    if username.strip().lower() == admin.username and not request.active:
        raise HTTPException(status_code=400, detail="Kendi admin hesabınızı pasifleştiremezsiniz.")
    try:
        user = auth_service.set_user_active(username, request.active)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    analytics.log_chat(
        {
            "session_id": "admin",
            "message": f"user_status:{username}:{request.active}",
            "confidence": 1,
            "handoff_recommended": False,
            "source_count": 0,
            "domain": "Admin",
            "risk_level": "orta",
            "response_time_ms": 1,
            "username": admin.username,
        }
    )
    return user


@app.get("/api/enterprise/overview", response_model=EnterpriseOverviewResponse)
def enterprise_overview(_: UserProfile = Depends(admin_user)) -> EnterpriseOverviewResponse:
    return enterprise.overview()


@app.get("/api/admin/audit", response_model=AuditTrailResponse)
def audit_trail(_: UserProfile = Depends(admin_user)) -> AuditTrailResponse:
    return AuditTrailResponse(events=enterprise.audit_events())


@app.get("/api/admin/tickets", response_model=TicketListResponse)
def list_tickets(_: UserProfile = Depends(admin_user)) -> TicketListResponse:
    return TicketListResponse(tickets=ops_service.list_tickets())


@app.patch("/api/admin/tickets/{ticket_id}", response_model=TicketRecord)
def update_ticket(ticket_id: str, request: TicketUpdateRequest, admin: UserProfile = Depends(admin_user)) -> TicketRecord:
    try:
        ticket = ops_service.update_ticket(
            ticket_id,
            status=request.status,
            assignee=request.assignee,
            priority=request.priority,
            resolution_note=request.resolution_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    analytics.log_chat(
        {
            "session_id": "admin",
            "message": f"ticket_updated:{ticket.id}:{ticket.status}",
            "confidence": 1,
            "handoff_recommended": False,
            "source_count": 0,
            "domain": "Admin",
            "risk_level": "düşük",
            "response_time_ms": 1,
            "username": admin.username,
        }
    )
    return ticket


@app.get("/api/support/tickets", response_model=TicketListResponse)
def list_support_tickets(_: UserProfile = Depends(support_user)) -> TicketListResponse:
    return TicketListResponse(tickets=ops_service.list_support_tickets())


@app.patch("/api/support/tickets/{ticket_id}", response_model=TicketRecord)
def update_support_ticket(ticket_id: str, request: TicketUpdateRequest, user: UserProfile = Depends(support_user)) -> TicketRecord:
    assignee = request.assignee
    if user.role == "support" and request.status in {"in_progress", "resolved"}:
        assignee = user.username
    try:
        ticket = ops_service.update_ticket(
            ticket_id,
            status=request.status,
            assignee=assignee,
            priority=request.priority,
            resolution_note=request.resolution_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    analytics.log_chat(
        {
            "session_id": "support",
            "message": f"support_ticket_updated:{ticket.id}:{ticket.status}",
            "confidence": 1,
            "handoff_recommended": ticket.escalation_required,
            "source_count": 0,
            "domain": ticket.category,
            "risk_level": "orta" if ticket.escalation_required else "düşük",
            "response_time_ms": 1,
            "username": user.username,
        }
    )
    return ticket


@app.get("/api/admin/integrations", response_model=IntegrationListResponse)
def list_integrations(_: UserProfile = Depends(admin_user)) -> IntegrationListResponse:
    return IntegrationListResponse(integrations=ops_service.list_integrations())


@app.patch("/api/admin/integrations/{integration_id}", response_model=IntegrationListResponse)
def update_integration(
    integration_id: str,
    request: IntegrationUpdateRequest,
    admin: UserProfile = Depends(admin_user),
) -> IntegrationListResponse:
    try:
        ops_service.update_integration(
            integration_id,
            status=request.status,
            enabled=request.enabled,
            endpoint=request.endpoint,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    analytics.log_chat(
        {
            "session_id": "admin",
            "message": f"integration_updated:{integration_id}",
            "confidence": 1,
            "handoff_recommended": False,
            "source_count": 0,
            "domain": "Admin",
            "risk_level": "düşük",
            "response_time_ms": 1,
            "username": admin.username,
        }
    )
    return IntegrationListResponse(integrations=ops_service.list_integrations())


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest, user: UserProfile = Depends(current_user)) -> ChatResponse:
    context = conversation_store.recent_context(request.session_id or user.id)
    enriched_message = request.message
    if context:
        enriched_message = f"Önceki konuşma bağlamı:\n{context}\n\nYeni soru: {request.message}"

    effective_role = "admin" if user.role == "admin" else (request.user_role or user.role)
    response = response_generator.answer(
        enriched_message,
        session_id=request.session_id,
        user_role=effective_role,
    )

    online_sources = []
    if should_use_online(request.message, request.online_enabled):
        online_sources = online_search.search(request.message)
        if online_sources:
            online_text = "\n\nOnline kaynak notu:\n" + "\n".join(f"- {source.excerpt}" for source in online_sources[:2])
            response.answer = f"{response.answer}{online_text}\nOnline bilgiler değişebileceği için kritik kararlarda resmi kaynakla doğrulayın."
            response.sources.extend(online_sources)
            response.confidence = max(response.confidence, 0.55)
        else:
            response.answer = f"{response.answer}\n\nOnline arama denendi fakat güvenilir kısa sonuç alınamadı. Daha spesifik bir arama terimi deneyebilirsiniz."

    conversation_store.append(response.session_id, "user", request.message, domain=response.domain)
    conversation_store.append(response.session_id, "assistant", response.answer, domain=response.domain, confidence=response.confidence)
    analytics.log_chat(
        {
            "session_id": response.session_id,
            "message": request.message,
            "confidence": response.confidence,
            "handoff_recommended": response.handoff_recommended,
            "source_count": len(response.sources),
            "domain": response.domain,
            "risk_level": response.risk_level,
            "response_time_ms": response.response_time_ms,
            "username": user.username,
            "online_sources": len(online_sources),
        }
    )
    return response


@app.post("/api/feedback", response_model=FeedbackResponse)
def feedback(request: FeedbackRequest, user: UserProfile = Depends(current_user)) -> FeedbackResponse:
    payload = request.model_dump()
    payload["username"] = user.username
    analytics.log_feedback(payload)
    return FeedbackResponse(status="received")


@app.get("/api/conversations/{session_id}", response_model=ConversationHistoryResponse)
def conversation_history(session_id: str, _: UserProfile = Depends(current_user)) -> ConversationHistoryResponse:
    return ConversationHistoryResponse(session_id=session_id, messages=conversation_store.history(session_id))


@app.post("/api/admin/reindex", response_model=HealthResponse)
def reindex(_: UserProfile = Depends(admin_user)) -> HealthResponse:
    knowledge_base.load()
    return HealthResponse(status="reindexed", indexed_chunks=len(knowledge_base.chunks), app_name=settings.app_name)


@app.get("/api/admin/documents", response_model=KnowledgeDocumentListResponse)
def list_documents(_: UserProfile = Depends(admin_user)) -> KnowledgeDocumentListResponse:
    return KnowledgeDocumentListResponse(documents=ops_service.list_documents())


@app.post("/api/admin/documents", response_model=KnowledgeDocumentResponse)
def add_document(request: KnowledgeDocumentRequest, user: UserProfile = Depends(admin_user)) -> KnowledgeDocumentResponse:
    path = enterprise.save_document(settings.knowledge_dir, request.title, request.content, request.category)
    knowledge_base.load()
    analytics.log_chat(
        {
            "session_id": "admin",
            "message": f"document_added:{path.name}",
            "confidence": 1,
            "handoff_recommended": False,
            "source_count": 0,
            "domain": "Admin",
            "risk_level": "düşük",
            "response_time_ms": 1,
            "username": user.username,
        }
    )
    return KnowledgeDocumentResponse(status="saved", path=path.as_posix(), indexed_chunks=len(knowledge_base.chunks))


@app.delete("/api/admin/documents/{filename}", response_model=KnowledgeDocumentResponse)
def delete_document(filename: str, user: UserProfile = Depends(admin_user)) -> KnowledgeDocumentResponse:
    try:
        ops_service.delete_document(filename)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    knowledge_base.load()
    analytics.log_chat(
        {
            "session_id": "admin",
            "message": f"document_deleted:{filename}",
            "confidence": 1,
            "handoff_recommended": False,
            "source_count": 0,
            "domain": "Admin",
            "risk_level": "orta",
            "response_time_ms": 1,
            "username": user.username,
        }
    )
    return KnowledgeDocumentResponse(status="deleted", path=filename, indexed_chunks=len(knowledge_base.chunks))


@app.post("/api/tickets/draft", response_model=TicketDraftResponse)
def draft_ticket(request: TicketDraftRequest, user: UserProfile = Depends(current_user)) -> TicketDraftResponse:
    requester = request.requester if user.role in {"admin", "support"} and request.requester else user.username
    return enterprise.draft_ticket(request.message, request.priority, requester)


@app.post("/api/tickets", response_model=TicketRecord)
def create_ticket(request: TicketCreateRequest, user: UserProfile = Depends(current_user)) -> TicketRecord:
    requester = request.requester if user.role in {"admin", "support"} and request.requester else user.username
    draft = enterprise.draft_ticket(request.message, request.priority, requester)
    ticket = ops_service.create_ticket(draft, requester)
    analytics.log_chat(
        {
            "session_id": "ticket",
            "message": f"ticket_created:{ticket.id}:{ticket.category}",
            "confidence": 1,
            "handoff_recommended": ticket.escalation_required,
            "source_count": 0,
            "domain": ticket.category,
            "risk_level": "orta" if ticket.escalation_required else "düşük",
            "response_time_ms": 1,
            "username": user.username,
        }
    )
    return ticket


@app.get("/api/tickets/me", response_model=TicketListResponse)
def my_tickets(user: UserProfile = Depends(current_user)) -> TicketListResponse:
    return TicketListResponse(tickets=ops_service.list_tickets_for_requester(user.username))
