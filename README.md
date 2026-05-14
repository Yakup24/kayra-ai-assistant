# Kayra AI Assistant

Türkçe çalışan, kaynaklı cevap üreten ve GitHub'a yüklemeye hazır bir chatbot başlangıç projesi.

Kurumsal kullanım, müşteri desteği, İK/IT destek süreçleri ve doküman tabanlı soru-cevap senaryoları için tasarlanmış FastAPI tabanlı Türkçe RAG asistanı.

Bu MVP şunları içerir:

- FastAPI tabanlı chat API
- Anahtarsız çalışan basit RAG/arama katmanı
- Türkçe metin normalizasyonu ve BM25 benzeri sıralama
- Kaynak gösterimli cevaplar
- Kurumsal görünümlü web sohbet arayüzü
- Rol seçimi: genel, çalışan, IT, İK ve destek
- Alan, güven skoru, risk seviyesi ve sonraki aksiyon üretimi
- API'den gelen konu başlıkları
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

## API Kullanımı

```bash
curl -X POST http://127.0.0.1:8000/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"İade süreci nasıl işliyor?\"}"
```

Örnek yanıt:

```json
{
  "answer": "Kaynaklara göre iade talebi...",
  "confidence": 0.82,
  "sources": [
    {
      "title": "E-Ticaret Müşteri Desteği",
      "path": "data/knowledge/e_ticaret.md",
      "score": 6.4
    }
  ],
  "domain": "Müşteri destek",
  "risk_level": "düşük",
  "response_time_ms": 12,
  "follow_up_suggestions": ["Canlı temsilciye aktar", "Benzer konu başlıklarını göster"],
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

## Proje Yapısı

```text
app/
  main.py                  FastAPI uygulaması
  schemas.py               API şemaları
  config.py                Ortam ve yol ayarları
  services/
    rag.py                 Doküman yükleme, parçalama ve arama
    response.py            Chat cevap üretimi
    privacy.py             Veri maskeleme yardımcıları
    analytics.py           Basit olay kaydı ve feedback
  static/
    index.html             Web arayüzü
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
docker build -t turkce-chatbot .
docker run --rm -p 8000:8000 turkce-chatbot
```

veya:

```bash
docker compose up --build
```

## Test

```bash
pytest
```

## Üretime Geçerken

Bu proje bilinçli olarak sade tutuldu. Üretim ortamında aşağıdaki geliştirmeler önerilir:

- RAG için PostgreSQL + pgvector, Qdrant, Weaviate veya Elasticsearch kullanımı
- Kullanıcı bazlı yetkilendirme ve doküman erişim kontrolü
- LLM entegrasyonu ve grounded generation prompt'ları
- Prometheus/Grafana, Sentry ve merkezi loglama
- Kalıcı feedback paneli ve kalite değerlendirme iş akışı
- KVKK aydınlatma metni, saklama politikası ve veri silme süreçleri
