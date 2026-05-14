# Kayra Enterprise Entegrasyon Kılavuzu

Kayra, web chat dışında e-posta, ticket ve takım içi mesajlaşma kanallarına bağlanabilecek şekilde tasarlanmalıdır. Her entegrasyon ayrı adaptör olarak ele alınır; ana sohbet motoru entegrasyon detaylarına bağımlı kalmaz.

## Microsoft Graph ve e-posta

Microsoft Graph veya Exchange entegrasyonu ile destek e-postaları okunur, sınıflandırılır ve cevap taslağı hazırlanır. Kullanıcı onayı olmadan e-posta gönderilmemelidir. Hassas veri içeren ekler maskelenmeli ve audit kaydına işlenmelidir.

## Jira ve ServiceNow ticket akışı

Chat mesajından kategori, öncelik, özet ve kabul kriterleri çıkarılarak ticket taslağı oluşturulur. Üretimde Jira veya ServiceNow REST API ile issue/incident kaydı açılır. Kritik veya KVKK içeren talepler otomatik eskalasyon kuralına bağlanmalıdır.

## Teams ve Slack

Teams veya Slack botları aynı chat API'sini kullanabilir. Kanal adaptörü kullanıcı kimliğini, rolünü ve tenant bilgisini API'ye taşır. Yanıtlar kısa, kaynaklı ve aksiyon butonlarıyla birlikte dönmelidir.

## Webhook ve CRM

CRM, ERP veya özel iş uygulamalarına outbound webhook ile olay gönderilebilir. Örneğin düşük güvenli yanıtlar kalite kuyruğuna, canlı destek talepleri destek CRM sistemine aktarılabilir.

