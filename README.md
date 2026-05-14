# Kayra Enterprise Assistant

Türkçe kurumsal destek süreçleri için geliştirilmiş, kaynaklı cevap üreten RAG tabanlı AI destek platformu prototipi.

Kayra; müşteri destek, IT, İK, uyumluluk, operasyon, ticket taslağı, audit ve admin bilgi tabanı yönetimi gibi kurumsal akışları tek uygulamada gösteren FastAPI tabanlı bir enterprise assistant örneğidir.

## Özellikler

- FastAPI tabanlı chat API
- Anahtarsız çalışan RAG/arama katmanı
- Türkçe metin normalizasyonu ve BM25 benzeri sıralama
- Kaynak gösterimli cevaplar
- Enterprise control center arayüzü
- Rol seçimi: genel, çalışan, IT, İK ve destek
- Alan, güven skoru, risk seviyesi ve sonraki aksiyon üretimi
- Ticket taslağı üretimi
- Admin doküman ekleme ve yeniden indeksleme
- Audit trail ve operasyon metrikleri
- Entegrasyon durum paneli: Graph, Jira/ServiceNow, Qdrant/pgvector, SSO
- KVKK/GDPR için temel veri maskeleme örnekleri
- Feedback endpoint'i
- Docker desteği
- Pytest testleri

## Hızlı Başlangıç

Python 3.10+ önerilir.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Tarayıcıda açın:

```text
http://127.0.0.1:8000
```

Bu makinede 8000 doluysa:

```bash
python -m uvicorn app.main:app --reload --port 8001
```

## Chat API

```bash
curl -X POST http://127.0.0.1:8000/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"İade süreci nasıl işliyor?\",\"user_role\":\"support\"}"
```

Örnek yanıt:

```json
{
  "answer": "Müşteri destek kaynaklarına göre...",
  "confidence": 0.82,
  "domain": "Müşteri destek",
  "risk_level": "düşük",
  "response_time_ms": 12,
  "sources": [
    {
      "title": "E-Ticaret Müşteri Desteği",
      "path": "data/knowledge/e_ticaret.md",
      "score": 6.4,
      "excerpt": "Müşteri ürünü teslim aldıktan sonra..."
    }
  ],
  "next_actions": [
    {
      "label": "İade şartları",
      "prompt": "İade süresi ve şartları nelerdir?"
    }
  ],
  "handoff_recommended": false,
  "session_id": "..."
}
```

## Enterprise API'leri

Platform özeti:

```bash
curl http://127.0.0.1:8000/api/enterprise/overview
```

Audit akışı:

```bash
curl http://127.0.0.1:8000/api/admin/audit
```

Ticket taslağı:

```bash
curl -X POST http://127.0.0.1:8000/api/tickets/draft ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"VPN erişim sorunu var\",\"priority\":\"acil\"}"
```

Bilgi tabanına doküman ekleme:

```bash
curl -X POST http://127.0.0.1:8000/api/admin/documents ^
  -H "Content-Type: application/json" ^
  -d "{\"title\":\"Yeni Politika\",\"content\":\"En az 20 karakterlik kurumsal bilgi metni\",\"category\":\"İK\"}"
```

## Proje Yapısı

```text
app/
  main.py                  FastAPI uygulaması ve endpointler
  schemas.py               API şemaları
  config.py                Ortam ve yol ayarları
  services/
    rag.py                 Doküman yükleme, parçalama ve arama
    response.py            Chat cevap üretimi
    enterprise.py          Enterprise overview, audit, ticket ve admin servisleri
    privacy.py             Veri maskeleme yardımcıları
    analytics.py           Olay kaydı, feedback ve metrik özetleri
  static/
    index.html             Enterprise web arayüzü
    styles.css
    app.js
data/
  knowledge/               RAG bilgi tabanı dokümanları
tests/
```

## Bilgi Tabanı Güncelleme

Yeni kaynak eklemek için `data/knowledge` klasörüne `.md` veya `.txt` dosyası koyun. Sunucu çalışırken yeniden indekslemek için:

```bash
curl -X POST http://127.0.0.1:8000/api/admin/reindex
```

## Docker ile Çalıştırma

```bash
docker build -t kayra-enterprise-assistant .
docker run --rm -p 8000:8000 kayra-enterprise-assistant
```

veya:

```bash
docker compose up --build
```

## Test

```bash
python -m pytest
```

## Üretime Geçerken

Bu prototip üretim mimarisine yakın bir iskelet sunar. Gerçek kurumsal ortam için şu geliştirmeler önerilir:

- PostgreSQL + pgvector veya Qdrant ile kalıcı vektör arama
- Azure AD/Okta SSO, JWT ve rol bazlı doküman erişimi
- OpenAI/Azure OpenAI LLM gateway ve prompt/version yönetimi
- Microsoft Graph, Jira, ServiceNow, Teams ve Slack adaptörleri
- Redis/Celery ile e-posta, ticket ve doküman işleme kuyruğu
- Prometheus/Grafana, Sentry, merkezi loglama ve OpenTelemetry
- KVKK aydınlatma metni, saklama politikası ve veri silme süreçleri
