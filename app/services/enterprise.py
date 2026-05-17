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
    ProductionReadinessResponse,
    ReadinessCheck,
    RoadmapItem,
    SecurityControl,
    TicketDraftResponse,
    TicketRecord,
    UserProfile,
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
        description="Çalışan mesajından kategori, öncelik, özet ve kabul kriteri çıkarır.",
        status="Prototip",
    ),
    Capability(
        title="SLA ve çözüm puanı",
        description="Ticket önceliğine göre hedef süre belirler; çözülünce süre ve 100 üzerinden kapanış puanı hesaplar.",
        status="Aktif",
    ),
    Capability(
        title="RBAC uyumlu rol bağlamı",
        description="Admin, destek uzmanı ve çalışan rollerini ayrı yetki alanlarıyla yönetir.",
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
        description="SSO sonrası çalışan rolüne göre doküman ve aksiyon yetkisi uygulanacak.",
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
            PlatformMetric(label="Feedback ort.", value=str(summary["avg_rating"] or "-"), trend="Çalışan puanı"),
        ]
        return EnterpriseOverviewResponse(
            product_name="Kayra Enterprise Assistant",
            tagline="Türkçe kurumsal destek, RAG, audit ve entegrasyon odaklı AI asistan platformu.",
            maturity="Enterprise Prototype v0.3",
            metrics=metrics,
            capabilities=CAPABILITIES,
            integrations=INTEGRATIONS,
            security_controls=SECURITY_CONTROLS,
            roadmap=ROADMAP,
        )

    def production_readiness(
        self,
        *,
        users: list[UserProfile],
        tickets: list[TicketRecord],
        integrations: list,
        documents: list,
        auth_secret_is_default: bool,
        allowed_origins: list[str],
        token_ttl_hours: int,
        refresh_token_ttl_hours: int,
    ) -> ProductionReadinessResponse:
        support_count = sum(1 for user in users if user.role == "support" and user.active)
        admin_count = sum(1 for user in users if user.role == "admin" and user.active)
        employee_count = sum(1 for user in users if user.role == "employee" and user.active)
        open_tickets = sum(1 for ticket in tickets if ticket.status != "resolved")
        breached_tickets = sum(1 for ticket in tickets if ticket.sla_status == "breached")
        enabled_integrations = sum(1 for item in integrations if item.enabled)
        strict_origins = "*" not in allowed_origins

        checks = [
            self._check(
                "auth-refresh",
                "Refresh token ve oturum süresi",
                "Güvenlik",
                token_ttl_hours <= 24 and refresh_token_ttl_hours >= token_ttl_hours,
                "Token süreleri yapılandırılmış.",
                f"Access token {token_ttl_hours} saat, refresh token {refresh_token_ttl_hours} saat.",
                "Access tokenı 8-12 saat, refresh tokenı 7 gün civarında tut; prod ortamda token blacklist/rotation ekle.",
                severity="high",
            ),
            self._check(
                "auth-secret",
                "Üretim secret kontrolü",
                "Güvenlik",
                not auth_secret_is_default,
                "AUTH_SECRET varsayılan değil.",
                "Varsayılan geliştirme secretı kullanılıyor.",
                "Canlıya çıkmadan AUTH_SECRET değerini uzun ve rastgele bir secret ile değiştir.",
                severity="critical",
            ),
            self._check(
                "cors",
                "CORS origin kısıtı",
                "Güvenlik",
                strict_origins,
                "ALLOWED_ORIGINS kısıtlı.",
                f"Origin listesi: {', '.join(allowed_origins)}",
                "Canlı domain dışında origin bırakma; wildcard kullanma.",
                severity="high",
            ),
            self._check(
                "rbac",
                "Rol bazlı erişim",
                "Güvenlik",
                admin_count >= 1 and support_count >= 1,
                f"{admin_count} admin ve {support_count} destek hesabı aktif.",
                "Admin/destek rol ayrımı eksik.",
                "600 çalışan senaryosu için 4 admin, 10 destek uzmanı ve departman bazlı izin modeli kur.",
                severity="high",
            ),
            self._check(
                "sqlite",
                "Veritabanı ölçek hazırlığı",
                "Veri",
                False,
                "PostgreSQL/pgvector hazır.",
                "Şu an SQLite prototip veritabanı kullanılıyor.",
                "Canlıda PostgreSQL + Alembic migration + günlük yedek + SSL bağlantı kullan.",
                severity="critical",
            ),
            self._check(
                "rag",
                "RAG kaynak kapsamı",
                "AI/RAG",
                len(documents) >= 6,
                f"{len(documents)} bilgi tabanı dokümanı var.",
                f"Sadece {len(documents)} doküman var.",
                "600 çalışan için PDF/Office import, chunking, embedding ve pgvector/Qdrant indeksine geç.",
                severity="medium",
            ),
            self._check(
                "integrations",
                "Kurumsal entegrasyonlar",
                "Entegrasyon",
                enabled_integrations >= 1,
                f"{enabled_integrations} entegrasyon aktif.",
                "Entegrasyonlar henüz çoğunlukla plan/adaptör seviyesinde.",
                "SSO, mail ve ticket sistemi için en az Azure AD/Okta, Graph ve Jira/ServiceNow bağlantılarını aktif et.",
                severity="medium",
            ),
            self._check(
                "sla",
                "SLA ve destek kapasitesi",
                "Operasyon",
                support_count >= 10 and breached_tickets == 0,
                f"Açık ticket: {open_tickets}, SLA aşan: {breached_tickets}, destek uzmanı: {support_count}.",
                f"Açık ticket: {open_tickets}, SLA aşan: {breached_tickets}, destek uzmanı: {support_count}.",
                "10 teknik uzman hedefi için destek hesaplarını tamamla; SLA aşan ticketlarda otomatik uyarı ekle.",
                severity="high",
            ),
            self._check(
                "audit",
                "Audit ve izleme",
                "Operasyon",
                True,
                "Chat, auth, ticket ve admin olayları audit/log akışına yazılıyor.",
                "Audit akışı yok.",
                "Prod için JSONL yerine merkezi loglama, Sentry, Prometheus/Grafana ve alarm kanalları ekle.",
                severity="medium",
            ),
            self._check(
                "ci",
                "CI/CD temel kontroller",
                "DevOps",
                True,
                "Pytest, compile ve Docker build GitHub Actions içinde koşuyor.",
                "CI/CD yok.",
                "Pipeline'a coverage, bandit, dependency scan ve container image publish adımları ekle.",
                severity="medium",
            ),
        ]

        weights = {"critical": 18, "high": 12, "medium": 8, "low": 4}
        total = sum(weights[check.severity] for check in checks)
        earned = sum(weights[check.severity] for check in checks if check.status == "passed")
        score = int((earned / max(total, 1)) * 100)
        maturity = "Prod adayı" if score >= 80 else "Pilot hazır" if score >= 55 else "Prototip"
        next_steps = [check.recommendation for check in checks if check.status != "passed"][:5]
        return ProductionReadinessResponse(
            generated_at=datetime.now(timezone.utc).isoformat(),
            target_profile="600 çalışan, 10 teknik destek uzmanı, 4 admin",
            score=score,
            maturity=maturity,
            summary=f"Kayra {maturity.lower()} seviyesinde. En kritik açıklar: veritabanı ölçeği, prod secret/CORS, SSO/MFA ve kurumsal entegrasyonlar.",
            checks=checks,
            next_steps=next_steps,
            capacity_plan={
                "employees_target": 600,
                "support_target": 10,
                "admin_target": 4,
                "active_employees": employee_count,
                "active_support": support_count,
                "active_admins": admin_count,
                "open_tickets": open_tickets,
                "breached_tickets": breached_tickets,
                "recommended_db": "PostgreSQL + pgvector veya Qdrant",
                "recommended_runtime": "Docker Compose pilot, Kubernetes production",
                "recommended_observability": "Prometheus/Grafana + Sentry + merkezi log",
            },
        )

    def _check(
        self,
        check_id: str,
        title: str,
        category: str,
        passed: bool,
        passed_evidence: str,
        failed_evidence: str,
        recommendation: str,
        *,
        severity: str,
    ) -> ReadinessCheck:
        return ReadinessCheck(
            id=check_id,
            title=title,
            category=category,
            status="passed" if passed else "action_required",
            severity=severity,
            evidence=passed_evidence if passed else failed_evidence,
            recommendation=recommendation,
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
