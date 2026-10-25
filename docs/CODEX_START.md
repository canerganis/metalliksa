# Codex başlangıç ve doğrulama

Aktif uygulama bu repo, üst `metalliksaa` ayrı repo. Komutları bu uygulama klasöründe çalıştır. `AGENTS.md` ve `RULES.md` bağlayıcıdır; bu dosya pratik giriş noktasıdır.

1. `git status --short`, `git log -1`, `STATUS.md` içindeki en güncel devam noktası ve ilgili aktif planı kontrol et. Başka worktree'nin başarısını bu checkout'un testi sayma.
2. Yalnız değişen alanın sözleşmesini oku. LPBF/fizik için `docs/LPBF_ENGINEERING.md`, `docs/LPBF_INTEGRATION_CONSTRAINTS.md` ve ilgili freeze/benchmark kayıtlarını kontrol et. UI/backend aynı kararı ikinci kez hesaplamaz; Python bilimsel otoritedir.
3. `package.json`, `.nvmrc` ve `.github/workflows/ci.yml` gerçek çalıştırma tanımlarıdır. Mevcut bağımlılıkları kontrol et; tam suite ve GPU bağımlılıklarını otomatik kurma.

## Göreve uygun komut

- Geliştirme: `npm run dev` (Node ortamı ve mevcut bağımlılıklar hazırsa).
- TypeScript kontrolü: `npm run lint`; ilgili UI/unit davranışı: `npm run test:unit`. Tüm uygulamanın çalıştığı iddiası için gerçek akışı ayrıca doğrula.
- Dar CPU sabit testi: `python/` klasöründe Python 3.12 ile `python -B -m unittest test_physical_constants`.
- LPBF Build Job: uygulama kökünde `npm run test:lpbf`; bunun varsayılanı fast suite, `test:lpbf:slow` ayrı kapsamdır. Fizik değişikliğinde aktif planın gerektirdiği sayısal/parity kapıları ayrıca uygulanır.
- Kod düzeltmesinde mümkünse önce hatayı göster, sonra davranışa yönelik regression testi çalıştır. Sade doküman değişikliğinde kaynak, bağlantı ve diff kontrolü yeterlidir.

## Teslim

Gerçek komut/exit ve sonuçları kaydet; eski STATUS sayıları güncel PASS değildir. Bilinen FAIL/SKIP/UNVALIDATED durumlarını gizleme. Kullanıcı değişikliklerini koru; yalnız kendi farkını stage edip yerel commit et. Push/yayın ayrıca yetki ister. Bu rehber, dondurulmuş fizik, test beklenenleri veya bilimsel kabul sınırını değiştirme yetkisi vermez.
