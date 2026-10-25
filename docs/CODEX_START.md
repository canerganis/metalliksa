# Codex başlangıcı

Uygulama kökünde çalış; üst `metalliksaa` ayrı repodur. `AGENTS.md` ve `RULES.md` bağlayıcıdır.

- Önce `git status --short`, `git log -1`, güncel `STATUS.md` ve ilgili plan. Fizik işinde yalnız ilgili LPBF sözleşmesi/freeze kaydını aç. Bilimsel otorite Python'dur; UI kararı tekrar hesaplamaz.
- Gerçek komut kaynağı: `package.json`, `.nvmrc`, `.github/workflows/ci.yml`.
- Geliştirme: `npm run dev`; TypeScript: `npm run lint`; ilgili unit davranışı: `npm run test:unit`.
- Dar CPU kontrolü: `python/` içinde Python 3.12 ile `python -B -m unittest test_physical_constants`. Build Job: kökte `npm run test:lpbf`; slow/parity kontrolleri aktif plan gerekiyorsa.
- Belge değişikliğinde içerik/bağlantı/diff yeterli. Fizik ve UI değişikliğini ilgili sayısal/gerçek akış kontrolüyle doğrula; çalıştırılmayanı belirt. Eski STATUS sayısı güncel PASS değildir.
- Yalnız kendi farkını yerel commit et; kullanıcı değişiklikleri ve frozen kabul sınırları korunur. Push/yayın ayrıca yetki ister. Sonuç, kontrol ve kalan sınırı kısa bildir.
