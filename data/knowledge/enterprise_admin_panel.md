# Kayra Enterprise Admin Panel Tasarımı

Admin paneli, platform sahiplerinin bilgi tabanını, kullanıcı rollerini, audit kayıtlarını, entegrasyon durumlarını ve kalite metriklerini yönetmesini sağlar. MVP aşamasında panel tek uygulama içinde özet bileşenler olarak sunulabilir.

## Bilgi tabanı yönetimi

Yetkili kullanıcılar yeni doküman ekleyebilir, var olan dokümanları güncelleyebilir ve yeniden indeksleme başlatabilir. Her dokümanda kategori, sahip ekip, güncelleme tarihi ve erişim seviyesi tutulmalıdır.

## Kalite yönetimi

Düşük güvenli yanıtlar, canlı destek önerilen konuşmalar ve olumsuz feedbackler ayrı bir kalite kuyruğunda izlenmelidir. Kalite ekibi bu örneklerden yeni doküman ihtiyacı, prompt iyileştirmesi veya entegrasyon ihtiyacı çıkarır.

## Operasyon paneli

Panelde toplam sohbet sayısı, ortalama güven, aktarım oranı, ortalama yanıt süresi, kaynak bulunamayan sorular ve feedback skoru gösterilmelidir. Bu metrikler üretimde Prometheus/Grafana ile desteklenmelidir.

## Entegrasyon yönetimi

Graph, Jira, ServiceNow, Teams, Slack ve webhook bağlantıları ortam değişkenleriyle yapılandırılır. Admin paneli bağlantı durumunu, son senkronizasyon zamanını ve hata mesajlarını göstermelidir.
