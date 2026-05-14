from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.schemas import ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse, HealthResponse, Topic, TopicsResponse
from app.services.analytics import AnalyticsLogger
from app.services.rag import KnowledgeBase
from app.services.response import ResponseGenerator


settings = get_settings()
knowledge_base = KnowledgeBase(settings.knowledge_dir)
response_generator = ResponseGenerator(knowledge_base, settings.min_confidence)
analytics = AnalyticsLogger(settings.log_dir)

TOPICS = [
    Topic(id="returns", title="İade ve Kargo", category="Müşteri Destek", prompt="İade süreci nasıl işliyor?"),
    Topic(id="vpn", title="VPN ve Erişim", category="IT Destek", prompt="VPN bağlantı hatasında ne yapmalıyım?"),
    Topic(id="leave", title="Yıllık İzin", category="İK", prompt="Yıllık izin prosedürü nedir?"),
    Topic(id="privacy", title="KVKK ve Gizlilik", category="Uyumluluk", prompt="Kişisel veri paylaşmadan nasıl destek alabilirim?"),
    Topic(id="ops", title="SLA ve İzleme", category="Operasyon", prompt="Kurumsal chatbot için SLA ve izleme nasıl kurulmalı?"),
]

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", indexed_chunks=len(knowledge_base.chunks), app_name=settings.app_name)


@app.get("/api/topics", response_model=TopicsResponse)
def topics() -> TopicsResponse:
    return TopicsResponse(topics=TOPICS)


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    response = response_generator.answer(
        request.message,
        session_id=request.session_id,
        user_role=request.user_role,
    )
    analytics.log_chat(
        {
            "session_id": response.session_id,
            "message": request.message,
            "confidence": response.confidence,
            "handoff_recommended": response.handoff_recommended,
            "source_count": len(response.sources),
        }
    )
    return response


@app.post("/api/feedback", response_model=FeedbackResponse)
def feedback(request: FeedbackRequest) -> FeedbackResponse:
    analytics.log_feedback(request.model_dump())
    return FeedbackResponse(status="received")


@app.post("/api/admin/reindex", response_model=HealthResponse)
def reindex() -> HealthResponse:
    knowledge_base.load()
    return HealthResponse(status="reindexed", indexed_chunks=len(knowledge_base.chunks), app_name=settings.app_name)
