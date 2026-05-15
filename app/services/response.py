from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from uuid import uuid4
import re

from app.schemas import ChatResponse, NextAction, Source
from app.services.rag import KnowledgeBase, SearchResult, TURKISH_ASCII_MAP, tokenize


DOMAIN_KEYWORDS = {
    "customer_support": {
        "iade", "kargo", "siparis", "sipariş", "urun", "ürün", "odeme", "ödeme", "teslimat", "musteri", "müşteri"
    },
    "it_support": {
        "vpn", "parola", "sifre", "şifre", "erisim", "erişim", "cihaz", "it", "mfa", "oturum", "hesap"
    },
    "hr": {
        "izin", "ik", "calisan", "çalışan", "yan", "hak", "portal", "yonetici", "yönetici"
    },
    "legal_privacy": {
        "hukuk", "hukuki", "kvkk", "gdpr", "gizlilik", "sozlesme", "sözleşme", "finansal", "yasal", "veri"
    },
    "operations": {
        "sla", "metrik", "rapor", "monitoring", "izleme", "performans", "olcekleme", "ölçekleme", "guvenlik", "güvenlik"
    },
}

DOMAIN_LABELS = {
    "customer_support": "Müşteri destek",
    "it_support": "IT destek",
    "hr": "İK ve çalışan deneyimi",
    "legal_privacy": "Hukuk, gizlilik ve uyumluluk",
    "operations": "Operasyon ve güvenlik",
    "general": "Genel bilgi",
}

GREETINGS = {"merhaba", "selam", "slm", "iyi gunler", "iyi günler", "gunaydin", "günaydın", "iyi aksamlar", "iyi akşamlar"}
HANDOFF_TERMS = {"temsilci", "insan", "musteri hizmetleri", "müşteri hizmetleri", "canli destek", "canlı destek", "yetkili"}
PROCEDURAL_TERMS = {
    "nasil",
    "nasıl",
    "kurulur",
    "yapilir",
    "yapılır",
    "adim",
    "adım",
    "cozum",
    "çözüm",
    "hata",
    "kontrol",
    "talimat",
}


@dataclass(frozen=True)
class Intent:
    name: str
    confidence: float
    domain: str


class ResponseGenerator:
    def __init__(self, knowledge_base: KnowledgeBase, min_confidence: float = 0.22) -> None:
        self.knowledge_base = knowledge_base
        self.min_confidence = min_confidence

    def answer(self, message: str, session_id: str | None = None, user_role: str | None = None) -> ChatResponse:
        started_at = perf_counter()
        session = session_id or str(uuid4())
        role = (user_role or "general").strip() or "general"
        intent = self._detect_intent(message)

        if intent.name == "greeting":
            return self._build_response(
                answer=(
                    "Merhaba, ben Kayra. Kurumsal bilgi tabanından kaynaklı yanıtlar hazırlayabilirim. "
                    "İade, IT destek, İK, uyumluluk ve operasyon konularında başlayabiliriz."
                ),
                confidence=0.96,
                sources=[],
                session_id=session,
                intent=intent,
                role=role,
                started_at=started_at,
                handoff=False,
                actions=[
                    NextAction(label="İade süreci", prompt="İade süreci nasıl işliyor?"),
                    NextAction(label="VPN desteği", prompt="VPN bağlantı hatasında ne yapmalıyım?"),
                    NextAction(label="Yıllık izin", prompt="Yıllık izin prosedürü nedir?"),
                ],
            )

        if intent.name == "handoff":
            return self._build_response(
                answer=(
                    "Canlı destek talebinizi not aldım. Aktarım için konu başlığı, aciliyet ve varsa sipariş ya da talep numarasını paylaşabilirsiniz. "
                    "Şifre, doğrulama kodu veya kart bilgisi yazmayın."
                ),
                confidence=0.92,
                sources=[],
                session_id=session,
                intent=intent,
                role=role,
                started_at=started_at,
                handoff=True,
                actions=[
                    NextAction(label="Acil talep", prompt="Canlı temsilciye aktar: acil bir destek talebim var."),
                    NextAction(label="Normal talep", prompt="Canlı temsilciye aktar: normal öncelikli destek istiyorum."),
                ],
            )

        results = self.knowledge_base.search(message)
        confidence = self._confidence(results)
        domain = self._domain_from_results(intent.domain, results)
        risk_level = self._risk_level(message, domain, confidence)
        intent = Intent(intent.name, intent.confidence, domain)

        if not results or confidence < self.min_confidence:
            return self._build_response(
                answer=(
                    "Bu soruya bilgi tabanındaki kaynaklarla güvenilir bir yanıt bulamadım. "
                    "Soruyu daha ayrıntılı yazabilir, ilgili dokümanı bilgi tabanına ekleyebilir veya canlı destek isteyebilirsiniz."
                ),
                confidence=confidence,
                sources=[],
                session_id=session,
                intent=intent,
                role=role,
                started_at=started_at,
                handoff=True,
                risk_level="orta",
                actions=[
                    NextAction(label="Soruyu netleştir", prompt=f"{message} konusunda daha ayrıntılı bilgi istiyorum."),
                    NextAction(label="Canlı destek", prompt="Canlı temsilciye aktar."),
                ],
            )

        answer_text = self._compose_answer(message, results, domain, risk_level, role)
        sources = [
            Source(
                title=result.chunk.title,
                path=result.chunk.path,
                score=result.score,
                excerpt=self._excerpt(result.chunk.text),
            )
            for result in results[:3]
        ]

        return self._build_response(
            answer=answer_text,
            confidence=confidence,
            sources=sources,
            session_id=session,
            intent=intent,
            role=role,
            started_at=started_at,
            handoff=confidence < 0.45 or risk_level == "yüksek",
            risk_level=risk_level,
            actions=self._next_actions(message, domain, confidence, risk_level),
        )

    def _build_response(
        self,
        *,
        answer: str,
        confidence: float,
        sources: list[Source],
        session_id: str,
        intent: Intent,
        role: str,
        started_at: float,
        handoff: bool,
        actions: list[NextAction],
        risk_level: str | None = None,
    ) -> ChatResponse:
        followups = [action.prompt for action in actions[:3]]
        return ChatResponse(
            answer=answer,
            confidence=confidence,
            sources=sources,
            follow_up_suggestions=followups,
            next_actions=actions,
            handoff_recommended=handoff,
            intent=intent.name,
            domain=DOMAIN_LABELS.get(intent.domain, DOMAIN_LABELS["general"]),
            risk_level=risk_level or self._risk_level("", intent.domain, confidence),
            response_time_ms=max(1, int((perf_counter() - started_at) * 1000)),
            session_id=session_id,
        )

    def _detect_intent(self, message: str) -> Intent:
        normalized = self._match_text(message)
        domain = self._detect_domain(normalized)
        if any(greeting in normalized for greeting in {self._match_text(item) for item in GREETINGS}) and len(tokenize(normalized)) <= 4:
            return Intent("greeting", 0.96, domain)
        if any(term in normalized for term in {self._match_text(item) for item in HANDOFF_TERMS}):
            return Intent("handoff", 0.92, domain)
        return Intent("question", 0.75, domain)

    def _detect_domain(self, normalized_message: str) -> str:
        scores: dict[str, int] = {}
        message_tokens = set(normalized_message.split()) | set(tokenize(normalized_message))
        for domain, keywords in DOMAIN_KEYWORDS.items():
            folded_keywords = {self._match_text(keyword) for keyword in keywords}
            score = len(message_tokens.intersection(folded_keywords))
            score += sum(1 for keyword in folded_keywords if keyword in normalized_message)
            if score:
                scores[domain] = score
        if not scores:
            return "general"
        return max(scores.items(), key=lambda item: item[1])[0]

    def _domain_from_results(self, detected_domain: str, results: list[SearchResult]) -> str:
        if detected_domain != "general" or not results:
            return detected_domain
        joined = " ".join(result.chunk.title for result in results[:2])
        return self._detect_domain(self._match_text(joined))

    def _risk_level(self, message: str, domain: str, confidence: float) -> str:
        normalized = self._match_text(message)
        high_risk_terms = {"hukuki", "finansal", "saglik", "sağlık", "kvkk", "gdpr", "kart", "kimlik", "sifre", "şifre"}
        if domain == "legal_privacy" or any(self._match_text(term) in normalized for term in high_risk_terms):
            return "yüksek"
        if confidence < 0.45:
            return "orta"
        return "düşük"

    def _confidence(self, results: list[SearchResult]) -> float:
        if not results:
            return 0.0
        top_score = results[0].score
        score = min(0.95, top_score / 7.5)
        if len(results) > 1 and results[1].score > 0:
            score += min(0.08, results[1].score / 30)
        return round(max(0.0, score), 2)

    def _compose_answer(self, message: str, results: list[SearchResult], domain: str, risk_level: str, role: str) -> str:
        if self._wants_steps(message):
            return self._compose_step_answer(message, results, domain, risk_level, role)

        selected_sentences = self._select_sentences(message, results)
        if not selected_sentences:
            selected_sentences = [self._excerpt(results[0].chunk.text, limit=320)]

        role_note = self._role_note(role, domain)
        lines = [f"{DOMAIN_LABELS.get(domain, DOMAIN_LABELS['general'])} kaynaklarına göre:"]
        for sentence in selected_sentences[:4]:
            lines.append(f"- {sentence}")
        if role_note:
            lines.append(role_note)
        if risk_level == "yüksek":
            lines.append("Not: Bu konu yüksek riskli olabilir; resmi işlem, hukuki/finansal karar veya kişisel veri paylaşımı için yetkili uzman onayı alınmalıdır.")
        else:
            lines.append("Gerekirse ilgili ekip veya canlı temsilci ile doğrulama yapılabilir.")
        return "\n".join(lines)

    def _compose_step_answer(self, message: str, results: list[SearchResult], domain: str, risk_level: str, role: str) -> str:
        selected_sentences = self._select_sentences(message, results)
        source_notes = selected_sentences[:3] or [self._excerpt(results[0].chunk.text, limit=280)]
        steps = self._procedural_steps(message, domain)

        lines = [f"{DOMAIN_LABELS.get(domain, DOMAIN_LABELS['general'])} kaynağını uygulanabilir adımlara çevirdim:"]
        for index, step in enumerate(steps, start=1):
            lines.append(f"{index}. {step}")
        lines.append("Kaynakta dayanak olan notlar:")
        for note in source_notes:
            lines.append(f"- {note}")
        role_note = self._role_note(role, domain)
        if role_note:
            lines.append(role_note)
        if risk_level == "yüksek":
            lines.append("Bu akış yüksek riskli olabilir; işlem öncesi yetkili uzman onayı alın.")
        lines.append("Sorun bu adımlarla çözülmezse ticket açıp hata mesajı, cihaz/hesap bilgisi ve denenen adımları ekleyin.")
        return "\n".join(lines)

    def _procedural_steps(self, message: str, domain: str) -> list[str]:
        normalized = self._match_text(message)
        if domain == "it_support" and "vpn" in normalized:
            return [
                "Kurumsal internet bağlantısını ve cihazın saat/tarih bilgisini kontrol edin.",
                "VPN uygulaması yüklü değilse kurum portalından onaylı istemciyi kurun; eski veya bilinmeyen istemci kullanmayın.",
                "Kurum e-posta hesabıyla oturum açın ve MFA/doğrulama bildirimini onaylayın.",
                "Bağlantı hata verirse uygulamayı kapatıp yeniden açın, sonra hata mesajını ekrana göründüğü gibi kaydedin.",
                "Hata devam ederse destek talebi açın; cihaz adı, işletim sistemi, lokasyon ve hata mesajını ekleyin.",
            ]
        if domain == "it_support":
            return [
                "Çalışandan şifre veya tek kullanımlık kod istemeden sorunun kapsamını doğrulayın.",
                "Cihaz, tarayıcı/uygulama, hata mesajı ve etkilenen hesabı kaydedin.",
                "Bilgi tabanındaki ilgili prosedürü uygulayın ve her adımın sonucunu not edin.",
                "Sorun devam ederse ticketı destek uzmanına atayıp önceliği güncelleyin.",
            ]
        if domain == "hr":
            return [
                "Çalışanın talep tipini ve gerekli tarih/bağlam bilgisini netleştirin.",
                "İlgili portal veya politika adımını kaynak dokümana göre uygulayın.",
                "Yönetici onayı, belge veya ek bilgi gerekiyorsa çalışana açıkça bildirin.",
                "Konu kişisel veri içeriyorsa sadece yetkili kanal üzerinden ilerleyin.",
            ]
        return [
            "Sorunun başlığını, etkilenen kişiyi ve beklenen sonucu netleştirin.",
            "Bilgi tabanındaki kaynak notlarını sırayla uygulayın.",
            "Her adım sonunda sonucun değişip değişmediğini kontrol edin.",
            "Çözüm olmazsa ticket açıp denenen adımları ve gözlenen hatayı ekleyin.",
        ]

    def _role_note(self, role: str, domain: str) -> str:
        normalized_role = self._match_text(role)
        if normalized_role in {"it", "admin"} and domain == "it_support":
            return "IT ekip notu: Kullanıcıdan şifre veya tek kullanımlık kod istemeden cihaz adı, işletim sistemi ve hata mesajı alın."
        if normalized_role in {"ik", "hr"} and domain == "hr":
            return "İK ekip notu: İzin ve yan hak yanıtlarında çalışanın portal kaydına yönlendirme yapılmalı."
        if normalized_role in {"destek", "support"} and domain == "customer_support":
            return "Destek ekip notu: Sipariş numarası istenebilir; kart bilgisi veya doğrulama kodu istenmemelidir."
        return ""

    def _select_sentences(self, message: str, results: list[SearchResult]) -> list[str]:
        query_tokens = set(tokenize(message))
        candidates: list[tuple[int, str]] = []

        for result in results[:3]:
            sentences = re.split(r"(?<=[.!?])\s+", result.chunk.text)
            for sentence in sentences:
                cleaned = sentence.strip()
                if len(cleaned) < 35:
                    continue
                overlap = len(query_tokens.intersection(tokenize(cleaned)))
                if overlap > 0:
                    candidates.append((overlap, cleaned))

        ordered = sorted(candidates, key=lambda item: item[0], reverse=True)
        seen: set[str] = set()
        sentences: list[str] = []
        for _, sentence in ordered:
            normalized = sentence.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            sentences.append(sentence)
        return sentences

    def _next_actions(self, message: str, domain: str, confidence: float, risk_level: str) -> list[NextAction]:
        if domain == "it_support":
            return [
                NextAction(label="Adım adım çöz", prompt=f"{message} için kaynağı adım adım uygulanacak çözüm planına çevir."),
                NextAction(label="Talep metni", prompt="IT destek kaydı için kısa talep metni hazırla."),
                NextAction(label="Canlı destek", prompt="Canlı temsilciye aktar."),
            ]
        if domain == "hr":
            return [
                NextAction(label="Portal adımları", prompt="Yıllık izin talebini portalda nasıl açarım?"),
                NextAction(label="Yan haklar", prompt="Yan haklar ne zaman aktif edilir?"),
                NextAction(label="İK'ya aktar", prompt="İK temsilcisine aktar."),
            ]
        if domain == "customer_support":
            return [
                NextAction(label="İade şartları", prompt="İade süresi ve şartları nelerdir?"),
                NextAction(label="Kargo durumu", prompt="Kargo teslimatı kaç gün sürer?"),
                NextAction(label="Temsilci", prompt="Canlı temsilciye aktar."),
            ]
        if risk_level == "yüksek":
            return [
                NextAction(label="Uzman onayı", prompt="Bu konuyu uzman onayı gerektirecek şekilde özetle."),
                NextAction(label="Veri güvenliği", prompt="Kişisel veri paylaşmadan nasıl ilerlemeliyim?"),
            ]
        if confidence < 0.45:
            return [
                NextAction(label="Netleştir", prompt=f"{message} konusunda daha fazla bağlamla yanıt ver."),
                NextAction(label="Kaynak ekle", prompt="Bu konu için bilgi tabanına hangi doküman eklenmeli?"),
            ]
        return [
            NextAction(label="Adım adım çöz", prompt=f"{message} için kaynağı adım adım uygulanacak çözüm planına çevir."),
            NextAction(label="Kaynaklar", prompt="Bu yanıtın kaynaklarını göster."),
            NextAction(label="Canlı destek", prompt="Canlı temsilciye aktar."),
        ]

    def _excerpt(self, text: str, limit: int = 180) -> str:
        compact = re.sub(r"\s+", " ", text).strip()
        if len(compact) <= limit:
            return compact
        return compact[: limit - 1].rstrip() + "…"

    def _match_text(self, text: str) -> str:
        return text.replace("İ", "i").replace("I", "ı").lower().translate(TURKISH_ASCII_MAP)

    def _wants_steps(self, message: str) -> bool:
        normalized = self._match_text(message)
        return any(self._match_text(term) in normalized for term in PROCEDURAL_TERMS)
