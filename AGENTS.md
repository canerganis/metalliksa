# Metalliksa — Agent Working Agreement

## Amaç ve süreklilik

- Yetkilendirilmiş işi inceleme, uygulama ve doğrulama ile tamamla.
- Küçük işlerde kısa ilerle; önemli değişikliklerde plan ve kabul ölçütleri oluştur.
- Kullanıcıyla Türkçe konuş; ürün dili, kayıt ve teslim için [RULES.md](RULES.md) dosyasını izle.
- Oturum veya compaction sonrası, devam notlarını ve çalışma ağacını gerekiyorsa kontrol et; tamamlanmış işleri tekrarlama.

## Kod keşfi

- Graft'ı yerel yön bulma ve kaynak aralıkları için; codebase-memory'yi ilişki, etki ve coverage sorguları için öncelikli kullan.
- Her soruda ikisini de çalıştırmak gerekmez. Yeni graph oturumunda proje ve generation bilgisini doğrula.
- Graft map, ask --source, skeleton ve callers araçlarını soru kapsamına göre seç.
- Dayanılan yollar için check_index_coverage kullan. Eksik/eski coverage veya yetersiz sonuçlarda ilgili kaynağı oku.
- Top-N arama sonucundan eksiksizlik çıkarma; kapsamlı iddialarda ilgili sayfaları ve kapsamı kontrol et.
- Metin, yapılandırma ve belgelerde rg kullan. Sözleşmeyi, hata davranışını ve çağıranları anlayacak kadar kaynak oku.
- Araç kullanılamıyorsa sınırı belirt ve kaynaklarla ilerle.
- Büyük kod değişikliklerinden sonra kullanılan yerel graph'ı güncelle.

## Araçlar ve iş bölümü

- Skill ve eklentileri somut ihtiyaca göre seç; sabit araç sırası zorunlu değildir.
- Araştırmada birincil kaynakları doğrula. Araştırma, UI, debugging ve test skill'lerini katkı sağladığında kullan.
- Bağımsız ve anlamlı işlerde alt ajan kullanılabilir. Önce ortak sözleşmeyi, dosya sahipliğini ve kabul kontrollerini belirle.
- Yerleşik alt ajanlar yeterliyse onları kullan. Codex Fleet ayrı CLI/worktree orkestrasyonu somut yarar sağladığında seçilir.
- Yeni fizik sözleşmesini önce tanımla; sonra API, UI ve doğrulamayı bağımsız kapsamlara ayır.
- Ana ajan entegrasyon ve son doğrulamadan sorumludur. Gemini dahil diğer ajanlarla koordinasyon RULES.md kapsamındadır.

## Bilimsel doğruluk

- Yazılım doğruluğu, sayısal doğrulama ve deneysel geçerlilik ayrı kanıt türleridir.
- Ölçülen, literatürden alınan, tahmin edilen, hesaplanan ve sentetik verileri ayır.
- Eksik girdileri uydurma veya başka alaşımdan sessizce tamamlama.
- Birimler, kaynaklar, varsayımlar, model sürümü ve geçerlilik sınırlarını kaydet.
- Proses değerlendirmesini yalnız VED'e dayandırma. Eşikler ve ışın yoğunluğu tanımları model/kaynak kapsamıyla değerlendirilir.
- Fizik değişikliğinden önce girdi/çıktı sözleşmesini ve kabul ölçütlerini yaz; onaylı plan yeterliyse rutin uygulama için tekrar onay isteme.
- Ölçüm tanımlarını eşleştir; kalibrasyon ve değerlendirme verilerini ayır.
- Başarısız benchmark'ı raporla; toleransı sonuca göre sessizce değiştirme.
- Sentetik veya solver çıktısını bağımsız deney kanıtı sayma.
- Qualification zinciri ve alan ayrıntıları [SCHEMA.md](docs/archive/SCHEMA.md) içindedir.

## Mimari sınırlar

- Mevcut React/TypeScript, Node ve Python mimarisini koru; yeni bağımlılıkları somut ihtiyaçla gerekçelendir.
- Bilimsel sonuçların otoritesi Python katmanıdır; arayüzde aynı sonucu üreten ikinci yol kurma.
- Ortak proses durumu activeSpecimen.lpbf; STL oturum geometrisi useLpbfBuildMeshStore; Build Job sonucu useLpbfBuildJobStore üzerinden yönetilir.
- Build Job kararını backend'den göster; UI içinde yeniden puanlama yapma.
- Ortak alaşım özelliklerinin mevcut kaynağı python/four_alloy_materials.py dosyasıdır; sabitleri solverlara kopyalama.
- Yeni mimariye geçişte uyumluluğu ve tek otorite ilkesini koru.
- Girdi değişince eski sonucu güncelmiş gibi gösterme.
- Mevcut Tailwind, lucide-react ve Zustand örüntülerini izle. Three.js kaynaklarını, animasyonları ve observer'ları temizle.
- Model veya benchmark entegrasyonu değiştirirken [LPBF entegrasyon kısıtlarını](docs/LPBF_INTEGRATION_CONSTRAINTS.md) oku; özel bilimsel sınırları koru.

## Göreve göre okunacak belgeler

- RULES.md: dil, kanıt, kayıt, commit ve ortak çalışma.
- docs/archive/SCHEMA.md: veri ve izlenebilirlik sözleşmesi.
- docs/LPBF_ENGINEERING.md: model tanımları ve bilimsel sınırlar.
- docs/RESEARCH_WORKSTATION.md: ürün akışları.
- docs/archive/MODULE_EVIDENCE_INVENTORY_2026-09-20.md: dated module inventory snapshot; do not use it as the live registry.
- Aktif plan: öncelikler, bağımlılıklar ve kabul kapıları.

Bütün belgeleri her oturumda yükleme. Değişken deney sonuçlarını burada tekrarlama.

Codex için ortam, dar test komutları ve teslim kontrolü: [docs/CODEX_START.md](docs/CODEX_START.md).

## Optional Graft context graph

Graft is available as a context source when its repository graph is useful. Direct source and documentation review, text search, and other tools are equally valid; no task requires Graft or a fixed tool order.
