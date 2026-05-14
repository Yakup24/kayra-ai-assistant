from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

from app.schemas import (
    AuditEvent,
    Capability,
    EnterpriseOverviewResponse,
    IntegrationStatus,
    PlatformMetric,
    RoadmapItem,
    SecurityControl,
    TicketDraftResponse,
)
from app.services.analytics import AnalyticsLogger
from app.services.privacy import mask_sensitive_data
from app.services.rag import KnowledgeBase, tokenize


CAPABILITIES = [
    Capability(
        title="Grounded RAG cevap motoru",
        description="Türkçe bilgi tabanından kaynak seçer, güven skoruyla yanıt üretir ve canlı destek eşiğini belirler.",
        status="Aktif",
    ),
    Capability(
        title="Enterprise control center",
        description="Operasyon, güvenlik, entegrasyon ve kalite metriklerini tek ekranda gösterir.",
        status="Aktif",
    ),
    Capability(
        title="Ticket ve e-posta taslakları",
        description="Kullanıcı mesajından kategori, öncelik, özet ve kabul kriteri çıkarır.",
        status="Prototip",
    ),
    Capability(
        title="RBAC uyumlu rol bağlamı",
        description="Genel, çalışan, IT, İK ve destek rolleriyle yanıt tonunu ve aksiyonları değiştirir.",
        status="Aktif",
    ),
]

INTEGRATIONS = [
    IntegrationStatus(
        name="Microsoft Graph / Exchange",
        category="E-posta",
        status="Planlandı",
        description="Gelen destek e-postalarını sınıflandırma, özetleme ve cevap taslağı üretme.",
    ),
    IntegrationStatus(
        name="Jira / ServiceNow",
        category="Ticket",
        status="Hazır adaptör",
        description="Chat akışından ticket taslağı üretme; gerçek REST entegrasyonu için ortam değişkenleriyle genişletilebilir.",
    ),
    IntegrationStatus(
        name="PostgreSQL + pgvector / Qdrant",
        category="Vektör DB",
        status="Planlandı",
        description="Mevcut hafif BM25 indeksinin üretimde vektör aramayla değiştirilmesi.",
    ),
    IntegrationStatus(
        name="Azure AD / Okta",
        category="SSO",
        status="Planlandı",
        description="OIDC tabanlı kimlik doğrulama, rol ve doküman erişim kontrolü.",
    ),
]

SECURITY_CONTROLS = [
    SecurityControl(
        title="PII maskeleme",
        level="Yüksek",
        description="TC kimlik, e-posta, telefon ve kart numarası loglara maskelenerek yazılır.",
    ),
    SecurityControl(
        title="Risk sınıflandırma",
        level="Yüksek",
        description="Hukuk, KVKK, finans, şifre ve kimlik konularında uzman onayı önerilir.",
    ),
    SecurityControl(
        title="Audit trail",
        level="Orta",
        description="Chat, feedback ve admin işlemleri JSONL tabanlı denetlenebilir olay olarak kaydedilir.",
    ),
    SecurityControl(
        title="Least privilege tasarımı",
        level="Plan",
        description="SSO sonrası kullanıcı rolüne göre doküman ve aksiyon yetkisi uygulanacak.",
    ),
]

ROADMAP = [
    RoadmapItem(phase="0-1 Ay", title="RBAC, audit ve admin doküman yönetimi", status="Devam", owner="Platform"),
    RoadmapItem(phase="1-3 Ay", title="Postgres/Qdrant RAG ve LLM gateway", status="Sırada", owner="AI"),
    RoadmapItem(phase="3-6 Ay", title="Graph, Jira, ServiceNow ve Teams entegrasyonları", status="Sırada", owner="Integration"),
    RoadmapItem(phase="6-12 Ay", title="Kubernetes, observability ve SLA panelleri", status="Plan", owner="DevOps"),
]


class EnterpriseService:
    def __init__(self, analytics: AnalyticsLogger, knowledge_base: KnowledgeBase) -> None:
        self.analytics = analytics
        self.knowledge_base = knowledge_base

    def overview(self) -> EnterpriseOverviewResponse:
        summary = self.analytics.summary()
        metrics = [
            PlatformMetric(label="İndekslenen parça", value=str(len(self.knowledge_base.chunks)), trend="Bilgi tabanı"),
            PlatformMetric(label="Toplam sohbet", value=str(summary["total_chats"]), trend="Son kayıtlar"),
            PlatformMetric(label="Ortalama güven", value=f"%{int(summary['avg_confidence'] * 100)}", trend="Yanıt kalitesi"),
            PlatformMetric(label="Aktarım önerisi", value=str(summary["handoffs"]), trend="Operasyon yükü"),
            PlatformMetric(label="Feedback ort.", value=str(summary["avg_rating"] or "-"), trend="Kullanıcı puanı"),
        ]
        return EnterpriseOverviewResponse(
            product_name="Kayra Enterprise Assistant",
            tagline="Türkçe kurumsal destek, RAG, audit ve entegrasyon odaklı AI asistan platformu.",
            maturity="Enterprise Prototype v0.2",
            metrics=metrics,
            capabilities=CAPABILITIES,
            integrations=INTEGRATIONS,
            security_controls=SECURITY_CONTROLS,
            roadmap=ROADMAP,
        )

    def audit_events(self, limit: int = 12) -> list[AuditEvent]:
        events = self.analytics.recent_events(limit)
        mapped: list[AuditEvent] = []
        for event in reversed(events):
            confidence = float(event.get("confidence", 0) or 0)
            risk = "orta" if confidence < 0.45 else "düşük"
            if event.get("handoff_recommended"):
                risk = "yüksek"
            mapped.append(
                AuditEvent(
                    created_at=str(event.get("created_at", "")),
                    event_type="chat",
                    summary=f"Mesaj işlendi · güven %{int(confidence * 100)} · kaynak {event.get('source_count', 0)}",
                    risk_level=risk,
                )
            )
        return mapped

    def save_document(self, knowledge_dir: Path, title: str, content: str, category: str) -> Path:
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        slug = self._slugify(title)
        path = knowledge_dir / f"{slug}.md"
        now = datetime.now(timezone.utc).isoformat()
        body = (
            f"# {title}\n\n"
            f"Kategori: {category}\n\n"
            f"Güncelleme: {now}\n\n"
            f"{mask_sensitive_data(content.strip())}\n"
        )
        path.write_text(body, encoding="utf-8")
        return path

    def draft_ticket(self, message: str, priority: str, requester: str | None = None) -> TicketDraftResponse:
        tokens = set(tokenize(message))
        category = "Genel Destek"
        if {"vpn", "parola", "erisim", "erişim", "sifre", "şifre"}.intersection(tokens):
            category = "IT Destek"
        elif {"izin", "ik", "calisan", "çalışan", "yan", "hak"}.intersection(tokens):
            category = "İK"
        elif {"iade", "kargo", "siparis", "sipariş", "odeme", "ödeme"}.intersection(tokens):
            category = "Müşteri Destek"
        elif {"kvkk", "gdpr", "hukuki", "veri", "gizlilik"}.intersection(tokens):
            category = "Uyumluluk"

        cleaned = mask_sensitive_data(re.sub(r"\s+", " ", message).strip())
        title = f"{category}: {cleaned[:72]}".rstrip()
        if requester:
            cleaned = f"Talep sahibi: {mask_sensitive_data(requester)}. {cleaned}"

        escalation = priority.lower() in {"acil", "kritik", "high", "urgent"} or category == "Uyumluluk"
        return TicketDraftResponse(
            title=title,
            priority=priority,
            category=category,
            summary=cleaned,
            acceptance_criteria=[
                "Talep kategorisi ve önceliği doğrulandı.",
                "Gerekli kaynak veya doküman bağlantısı eklendi.",
                "Kişisel veri, şifre ve doğrulama kodu paylaşılmadan ilerleniyor.",
            ],
            escalation_required=escalation,
        )

    def _slugify(self, text: str) -> str:
        normalized = text.lower()
        normalized = normalized.translate(str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u"}))
        normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
        return normalized or "dokuman"
