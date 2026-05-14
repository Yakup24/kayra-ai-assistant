# Kayra Enterprise Güvenlik ve KVKK Kontrolleri

Kurumsal AI asistanı kişisel veriye temas edebileceği için güvenlik tasarımı ürünün çekirdeğinde olmalıdır. Kayra, gereksiz veri toplamama, amaçla sınırlı işleme, maskeleme ve denetlenebilirlik ilkelerini takip eder.

## Kimlik ve yetki

Üretimde Azure AD, Okta veya benzeri OIDC sağlayıcılarıyla SSO kullanılmalıdır. Kullanıcı rolü JWT içinden okunur ve doküman erişimi rol bazlı kontrol edilir. Admin işlemleri MFA ve audit kaydı gerektirir.

## Veri maskeleme

TC kimlik numarası, telefon, e-posta, kart numarası, şifre ve tek kullanımlık kod gibi bilgiler loglara açık yazılmamalıdır. Kullanıcı bu bilgileri yazarsa sistem maskeler ve yanıtında bu verilerin paylaşılmaması gerektiğini belirtir.

## Retention ve audit

Chat logları, feedback ve admin işlemleri saklama politikasına bağlı tutulmalıdır. Kişisel veri barındıran kayıtlar gereğinden uzun saklanmamalıdır. Audit kayıtları kimin, ne zaman, hangi aksiyonu aldığını gösterecek şekilde tasarlanır.

## Riskli yanıt politikası

Hukuki, finansal, sağlık, KVKK, güvenlik ve kimlik bilgisi içeren konularda Kayra kesin hüküm vermez. Yanıt kaynaklara dayalı olsa bile yetkili uzman onayı önerilir ve gerekirse canlı destek aktarımı yapılır.

