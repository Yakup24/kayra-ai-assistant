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
    KnowledgeDocumentRequest,
    KnowledgeDocumentResponse,
    LoginRequest,
    RegisterRequest,
    TicketDraftRequest,
    TicketDraftResponse,
    Topic,
    TopicsResponse,
    UserProfile,
)
from app.services.analytics import AnalyticsLogger
from app.services.auth import AuthService
from app.services.conversation import ConversationStore
from app.services.enterprise import EnterpriseService
from app.services.online import OnlineSearchService
from app.services.rag import KnowledgeBase
from app.services.response import ResponseGenerator


settings = get_settings()
knowledge_base = KnowledgeBase(settings.knowledge_dir)
response_generator = ResponseGenerator(knowledge_base, settings.min_confidence)
analytics = AnalyticsLogger(settings.log_dir)
enterprise = EnterpriseService(analytics, knowledge_base)
auth_service = AuthService(
    settings.log_dir / "users.json",
    settings.auth_secret,
    settings.admin_username,
    settings.admin_password,
)
conversation_store = ConversationStore(settings.log_dir / "conversations")
online_search = OnlineSearchService()

TOPICS = [
    Topic(id="returns", title="İade ve Kargo", category="Müşteri Destek", prompt="İade süreci nasıl işliyor?"),
    Topic(id="vpn", title="VPN ve Erişim", category="IT Destek", prompt="VPN bağlantı hatasında ne yapmalıyım?"),
    Topic(id="leave", title="Yıllık İzin", category="İK", prompt="Yıllık izin prosedürü nedir?"),
    Topic(id="privacy", title="KVKK ve Gizlilik", category="Uyumluluk", prompt="Kişisel veri paylaşmadan nasıl destek alabilirim?"),
    Topic(id="ops", title="SLA ve İzleme", category="Operasyon", prompt="Kurumsal chatbot için SLA ve izleme nasıl kurulmalı?"),
    Topic(id="architecture", title="Mimari Yol Haritası", category="Platform", prompt="Kayra Enterprise mimarisi nasıl ölçeklenmeli?"),
]

app = FastAPI(title=settings.app_name, version="0.2.0")
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


@app.post("/api/auth/register", response_model=AuthResponse)
def register(request: RegisterRequest) -> AuthResponse:
    try:
        user = auth_service.register(request.username, request.password, request.email, request.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AuthResponse(token=auth_service.create_token(user), user=user)


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


@app.get("/api/enterprise/overview", response_model=EnterpriseOverviewResponse)
def enterprise_overview(_: UserProfile = Depends(admin_user)) -> EnterpriseOverviewResponse:
    return enterprise.overview()


@app.get("/api/admin/audit", response_model=AuditTrailResponse)
def audit_trail(_: UserProfile = Depends(admin_user)) -> AuditTrailResponse:
    return AuditTrailResponse(events=enterprise.audit_events())


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


@app.post("/api/tickets/draft", response_model=TicketDraftResponse)
def draft_ticket(request: TicketDraftRequest, user: UserProfile = Depends(current_user)) -> TicketDraftResponse:
    requester = request.requester or user.username
    return enterprise.draft_ticket(request.message, request.priority, requester)
