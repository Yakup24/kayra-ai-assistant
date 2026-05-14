# Kayra Enterprise Mimari Referansı

Kayra Enterprise Assistant, kurumsal destek süreçleri için modüler bir AI platformu olarak tasarlanır. Çekirdek katmanda FastAPI API Gateway, sohbet motoru, RAG arama katmanı, LLM gateway, audit/log servisi ve admin panel bulunur. Üretim ortamında bilgi tabanı PostgreSQL + pgvector veya Qdrant ile desteklenebilir.

## API Gateway ve servis sınırları

API Gateway kimlik doğrulama, rate limiting, istek doğrulama ve rol kontrolü için ilk giriş noktasıdır. Sohbet motoru kullanıcı mesajını sınıflandırır, risk seviyesini belirler ve RAG arama sonuçlarını yanıt motoruna aktarır. LLM gateway, OpenAI veya Azure OpenAI gibi servisleri tek bir soyutlama arkasında yönetir.

## RAG arama katmanı

RAG katmanı dokümanları parçalara böler, meta verileri saklar ve sorguyla en alakalı içerikleri bulur. MVP aşamasında BM25 benzeri hafif arama yeterlidir. Üretimde vektör arama, reranker, doküman erişim kontrolü ve kaynak kalitesi skoru eklenmelidir.

## Kuyruk ve arka plan işleme

E-posta okuma, ticket senkronizasyonu, dosya ayrıştırma ve toplu indeksleme işlemleri API isteğini bekletmeden arka planda çalışmalıdır. Redis ve Celery gibi bir kuyruk yapısı, işlerin yeniden denenmesini ve ölçeklenmesini kolaylaştırır.

## Üretim dağıtımı

Docker imajı CI/CD ile oluşturulur. Kubernetes üzerinde API, worker, cache, vektör veritabanı ve gözlemlenebilirlik bileşenleri ayrı deployment olarak çalıştırılır. Rolling update, health check, readiness probe ve otomatik ölçeklendirme kullanılmalıdır.

