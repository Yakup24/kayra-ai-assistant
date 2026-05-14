# Kurumsal Operasyon ve Üretim Kalitesi

## SLA ve destek akışı

Kurumsal chatbot canlıya alınırken destek seviyeleri açık tanımlanmalıdır. Kritik erişim, ödeme, kişisel veri ve güvenlik olayları yüksek öncelikli kabul edilir. Bot düşük güvenle yanıt verdiğinde veya kullanıcı canlı destek istediğinde talep kaydı oluşturulmalı ve ilgili ekibe aktarılmalıdır.

SLA hedefleri örnek olarak kritik konularda 15 dakika ilk yanıt, normal destek taleplerinde 4 saat ilk yanıt ve bilgi taleplerinde 1 iş günü çözüm şeklinde belirlenebilir. Bu hedefler kurumun destek kapasitesine göre güncellenmelidir.

## İzleme ve kalite metrikleri

Üretim ortamında yanıt süresi, başarı oranı, canlı temsilciye aktarım oranı, kullanıcı memnuniyeti, kaynak bulunamayan soru oranı ve en sık aranan konular izlenmelidir. Bu metrikler Prometheus, Grafana, Sentry veya bulut izleme servisleriyle takip edilebilir.

Kaynak bulunamayan sorular haftalık olarak incelenmeli ve bilgi tabanına yeni doküman ekleme sürecine bağlanmalıdır. Yanlış veya eksik cevaplar kalite etiketleriyle işaretlenmeli, gerekirse prompt ve retrieval ayarları güncellenmelidir.

## Güvenlik ve yetkilendirme

Bot kullanıcı rollerine göre cevap vermeli ve yetkisiz dokümanlara erişim sağlamamalıdır. Hassas sistemlerde rol bazlı erişim kontrolü, denetim logları, veri maskeleme ve kısa veri saklama süresi uygulanmalıdır. Şifre, tek kullanımlık doğrulama kodu, kart bilgisi ve özel nitelikli kişisel veri sohbet ekranında istenmemelidir.

## Üretime geçiş kontrol listesi

Canlıya çıkmadan önce bilgi tabanı sahipliği, veri saklama politikası, geri bildirim akışı, hata alarmı, yedekleme planı, konteyner güvenliği ve API rate limiting tamamlanmalıdır. Kritik alanlarda bot yanıtları kesin hüküm vermek yerine kaynak, belirsizlik ve uzman onayı bilgisini birlikte sunmalıdır.
