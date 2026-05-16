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
- SQLite tabanlı admin kontrollü çalışan ve destek hesabı veritabanı
- Ayrı giriş akışları: çalışan, destek uzmanı ve admin
- Destek uzmanı paneli: açık ticket kuyruğu, işleme alma ve çözüm notuyla kapatma
- Çalışan paneli: sorun/talep açma ve kendi ticket kayıtlarını takip etme
- Access token + refresh token akışı ile daha uzun ve kontrollü oturum yönetimi
- Argon2 destekli parola hashleme, geriye dönük PBKDF2 hash doğrulama
- Alan, güven skoru, risk seviyesi ve sonraki aksiyon üretimi
- Kaynak metnini çalışan için adım adım çözüm talimatına dönüştürme
- Ticket taslağı üretimi
- SQLite tabanlı kalıcı ticket kayıtları ve durum güncelleme
- Önceliğe göre SLA hedef süresi, çözülme süresi ve kapanışta 100 üzerinden çözüm puanı
- Ticket event geçmişi: oluşturma, işleme alma, durum değişikliği, kapanış ve yeniden açma kayıtları
- Escalation kuyruğu: yüksek riskli veya SLA süresi aşılmış taleplerin admin/destek tarafından izlenmesi
- Çözülen talepleri gerekçeyle yeniden açma
- Admin veri dışa aktarımı: kullanıcı, ticket, entegrasyon, doküman ve metrik özetleri
- Admin doküman ekleme ve yeniden indeksleme
- Bilgi tabanı doküman kataloğu
- Audit trail ve operasyon metrikleri
- Yönetilebilir entegrasyon durum paneli: Graph, Jira/ServiceNow, Qdrant/pgvector, SSO
- KVKK/GDPR için temel veri maskeleme örnekleri
- Güvenlik başlıkları: CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- Login, chat ve ticket endpointleri için basit rate limiting
- CORS izinlerini `ALLOWED_ORIGINS` ile ortam bazlı yönetme
- Ayarlanabilir token süresi (`TOKEN_TTL_HOURS`)
- Feedback endpoint'i
- Docker desteği
- Pytest testleri
- GitHub Actions CI

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
3. Admin panelindeki `Hesap Yönetimi` bölümünden çalışan hesabı oluşturun
4. Çalışan, admin tarafından verilen kullanıcı adı/şifre ile `Çalışan` sekmesinden giriş yapar
5. Sol panelden rol seçin: `Genel`, `Çalışan`, `IT`, `İK` veya `Destek`
6. `Online bilgi ara` seçeneğini açarsanız Kayra web kaynaklarından kısa ek bağlam çekmeyi dener
7. Destek uzmanı girişiyle çalışan talepleri kuyruğu, işleme alma ve çözüm notuyla kapatma ekranı açılır
8. Ticket kapanınca çözüm süresi ve SLA puanı otomatik hesaplanır
9. Çözülmeyen veya tekrar eden sorunlar `Yeniden aç` aksiyonuyla tekrar kuyruğa alınabilir
10. Admin girişiyle Control Center, audit, hesap, entegrasyon, ticket, escalation ve bilgi tabanı yönetimi açılır

Varsayılan geliştirme admin hesabı:

```text
Kullanıcı adı: admin
Şifre: KayraAdmin2026!
```

Varsayılan geliştirme destek uzmanı hesabı:

```text
Kullanıcı adı: support
Şifre: KayraSupport2026!
```

Üretimde `.env` ile `AUTH_SECRET`, `ADMIN_USERNAME` ve `ADMIN_PASSWORD` değerlerini değiştirin.
Destek hesabı için `SUPPORT_USERNAME` ve `SUPPORT_PASSWORD` değerlerini de güncelleyin veya admin panelinden yeni destek uzmanı oluşturun.
Tarayıcı origin listesi için `ALLOWED_ORIGINS`, access token süresi için `TOKEN_TTL_HOURS`, refresh token süresi için `REFRESH_TOKEN_TTL_HOURS`, istek sınırları için `LOGIN_RATE_LIMIT`, `API_RATE_LIMIT`, `TICKET_RATE_LIMIT` ve `RATE_LIMIT_WINDOW_SECONDS` kullanılabilir.

Not: Public/self kayıt yoktur. Kurumsal kullanımda çalışan ve destek uzmanı hesapları admin tarafından veritabanına eklenir.

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

Kayra kaynakları adım adım çözüm talimatına da dönüştürür:

```bash
curl -X POST http://127.0.0.1:8000/api/chat ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer TOKEN" ^
  -d "{\"message\":\"VPN nasıl kurulur adım adım anlat\",\"user_role\":\"employee\"}"
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
curl http://127.0.0.1:8000/api/admin/escalations -H "Authorization: Bearer TOKEN"
curl http://127.0.0.1:8000/api/admin/integrations -H "Authorization: Bearer TOKEN"
curl http://127.0.0.1:8000/api/admin/documents -H "Authorization: Bearer TOKEN"
curl http://127.0.0.1:8000/api/admin/export -H "Authorization: Bearer TOKEN"
```

Destek uzmanı ticket kuyruğu ve çözüm akışı:

```bash
curl http://127.0.0.1:8000/api/support/tickets -H "Authorization: Bearer TOKEN"

curl -X PATCH http://127.0.0.1:8000/api/support/tickets/KAYRA-1234ABCD ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer TOKEN" ^
  -d "{\"status\":\"resolved\",\"resolution_note\":\"Sorun incelendi ve çözüm adımları çalışana iletildi.\"}"
```

Ticket yanıtında `sla_minutes`, `sla_due_at`, `sla_status`, `resolution_minutes` ve `resolution_score` alanları döner.

Ticket event geçmişi:

```bash
curl http://127.0.0.1:8000/api/support/tickets/KAYRA-1234ABCD/events -H "Authorization: Bearer TOKEN"
```

Çözülen ticket'ı yeniden açma:

```bash
curl -X POST http://127.0.0.1:8000/api/tickets/KAYRA-1234ABCD/reopen ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer TOKEN" ^
  -d "{\"reason\":\"Sorun devam ediyor, VPN bağlantısı tekrar kesildi.\"}"
```

Çalışanın kendi talepleri:

```bash
curl http://127.0.0.1:8000/api/tickets/me -H "Authorization: Bearer TOKEN"
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
    auth.py                SQLite hesap veritabanı, Argon2/PBKDF2 parola hash ve token yönetimi
    ops.py                 Ticket, SLA, event geçmişi, escalation, entegrasyon ve doküman kataloğu servisleri
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
node --check app/static/app.js
```

GitHub Actions her `main` push ve pull request için compile, test ve Docker build kontrollerini otomatik çalıştırır:

```text
.github/workflows/ci.yml
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
- Refresh token rotation, token blacklist ve MFA
- OpenAI/Azure OpenAI LLM gateway ve prompt/version yönetimi
- Microsoft Graph, Jira, ServiceNow, Teams ve Slack adaptörleri
- Redis/Celery ile e-posta, ticket ve doküman işleme kuyruğu
- Prometheus/Grafana, Sentry, merkezi loglama ve OpenTelemetry
- KVKK aydınlatma metni, saklama politikası ve veri silme süreçleri
