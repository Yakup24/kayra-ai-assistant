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
- SQLite tabanlı admin kontrollü kullanıcı veritabanı
- Alan, güven skoru, risk seviyesi ve sonraki aksiyon üretimi
- Ticket taslağı üretimi
- SQLite tabanlı kalıcı ticket kayıtları ve durum güncelleme
- Admin doküman ekleme ve yeniden indeksleme
- Bilgi tabanı doküman kataloğu
- Audit trail ve operasyon metrikleri
- Yönetilebilir entegrasyon durum paneli: Graph, Jira/ServiceNow, Qdrant/pgvector, SSO
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

## Nasıl Kullanılır?

1. Uygulamayı açın: `http://127.0.0.1:8000` veya bu makinede `http://127.0.0.1:8001`
2. Admin hesabıyla giriş yapın
3. Admin panelindeki `Kullanıcı Yönetimi` bölümünden çalışan hesabı oluşturun
4. Çalışan, admin tarafından verilen kullanıcı adı/şifre ile giriş yapar
5. Sol panelden rol seçin: `Genel`, `Çalışan`, `IT`, `İK` veya `Destek`
6. `Online bilgi ara` seçeneğini açarsanız Kayra web kaynaklarından kısa ek bağlam çekmeyi dener
7. Admin girişiyle Control Center, audit, ticket studio ve bilgi tabanı yönetimi açılır

Varsayılan geliştirme admin hesabı:

```text
Kullanıcı adı: admin
Şifre: KayraAdmin2026!
```

Üretimde `.env` ile `AUTH_SECRET`, `ADMIN_USERNAME` ve `ADMIN_PASSWORD` değerlerini değiştirin.

Not: Public/self kayıt yoktur. Kurumsal kullanımda kullanıcılar admin tarafından veritabanına eklenir.

## Chat API

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"admin\",\"password\":\"KayraAdmin2026!\"}"
```

Sonra dönen token ile:

```bash
curl -X POST http://127.0.0.1:8000/api/chat ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer TOKEN" ^
  -d "{\"message\":\"İade süreci nasıl işliyor?\",\"user_role\":\"support\",\"online_enabled\":false}"
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
curl http://127.0.0.1:8000/api/enterprise/overview -H "Authorization: Bearer TOKEN"
```

Audit akışı:

```bash
curl http://127.0.0.1:8000/api/admin/audit -H "Authorization: Bearer TOKEN"
```

Ticket taslağı:

```bash
curl -X POST http://127.0.0.1:8000/api/tickets/draft ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer TOKEN" ^
  -d "{\"message\":\"VPN erişim sorunu var\",\"priority\":\"acil\"}"
```

Kalıcı ticket açma:

```bash
curl -X POST http://127.0.0.1:8000/api/tickets ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer TOKEN" ^
  -d "{\"message\":\"VPN erişim sorunu var\",\"priority\":\"acil\"}"
```

Admin operasyon listeleri:

```bash
curl http://127.0.0.1:8000/api/admin/tickets -H "Authorization: Bearer TOKEN"
curl http://127.0.0.1:8000/api/admin/integrations -H "Authorization: Bearer TOKEN"
curl http://127.0.0.1:8000/api/admin/documents -H "Authorization: Bearer TOKEN"
```

Bilgi tabanına doküman ekleme:

```bash
curl -X POST http://127.0.0.1:8000/api/admin/documents ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer TOKEN" ^
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
    auth.py                SQLite kullanıcı veritabanı, parola hash ve token yönetimi
    ops.py                 Ticket, entegrasyon ve doküman kataloğu servisleri
    conversation.py        Kayıtlı sohbet geçmişi
    online.py              Anahtarsız online bilgi arama adaptörü
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

## Lisans

Bu proje MIT lisansı ile yayınlanır.

- Copyright: `yakup eşki`
- GitHub: [https://github.com/Yakup24](https://github.com/Yakup24)
- Email: [yakup.eski2424@icloud.com](mailto:yakup.eski2424@icloud.com)

Detaylar için [LICENSE](LICENSE) ve [LICENSE.html](LICENSE.html) dosyalarına bakın.

Kişisel MIT lisans profili `remy/mit-license` yapısına uyumlu olacak şekilde ayrıca tutulur:

- [users/yakup24.json](users/yakup24.json)
- [license.config.json](license.config.json)

## Üretime Geçerken

Bu prototip üretim mimarisine yakın bir iskelet sunar. Gerçek kurumsal ortam için şu geliştirmeler önerilir:

- PostgreSQL + pgvector veya Qdrant ile kalıcı vektör arama
- Azure AD/Okta SSO, JWT ve rol bazlı doküman erişimi
- OpenAI/Azure OpenAI LLM gateway ve prompt/version yönetimi
- Microsoft Graph, Jira, ServiceNow, Teams ve Slack adaptörleri
- Redis/Celery ile e-posta, ticket ve doküman işleme kuyruğu
- Prometheus/Grafana, Sentry, merkezi loglama ve OpenTelemetry
- KVKK aydınlatma metni, saklama politikası ve veri silme süreçleri
