# rest-latex

Yüklenen LaTeX kaynaklarını kompakt bir Alpine konteyneri içinde PDF dosyalarına derleyen küçük bir FastAPI servisi. Ana makinede tam bir TeX dağıtımı kurmadan LaTeX çıktıları üretin.

## Genel Bakış
- Yüklenen `.tex` kaynaklarını (ve varsa ek varlıkları) PDF'e çeviren tek bir POST uç noktası.
- Varsayılan olarak Tectonic ile gelir; ortam değişkeniyle farklı motorlara geçebilirsiniz.
- CI/CD süreçleri ve kısa ömürlü işler için boyutu optimize edilmiş Alpine tabanlı imaj.

## Gereksinimler
- Docker 20.10 veya üzeri.
- API'yi test etmek için curl (veya herhangi bir HTTP istemcisi).

## Hızlı Başlangıç
1. İmajı oluşturun: `docker build -t rest-latex .`
2. API'yi 8080 portunda çalıştırın: `docker run --rm -p 8080:8080 rest-latex`
3. İsteğe bağlı: LuaLaTeX tercih etmek için `docker run` komutunda `LATEX_ENGINE=lualatex` ayarlayın.

## API

### POST `/compile`

**Form alanları**
- `tex_file` *(zorunlu)*: derlenecek LaTeX kaynak dosyası.
- `assets_archive` *(isteğe bağlı)*: kaynağın referans verdiği görselleri/fontları içeren ZIP dosyası.

**Örnekler**

Bağımsız bir `.tex` dosyasını derleyin:

```bash
curl \
  -X POST \
  -F "tex_file=@examples/sample.tex" \
  http://localhost:8080/compile \
  -o output.pdf
```

Harici varlıklarla derleyin:

```bash
curl \
  -X POST \
  -F "tex_file=@examples/sample_with_images.tex" \
  -F "assets_archive=@examples/assets.zip" \
  http://localhost:8080/compile \
  -o output.pdf
```

Servis, başarı durumunda PDF ek'i döner; derleme başarısız olduğunda ise `stdout`/`stderr` içeren bir JSON yanıtı verir.

### GET `/health`

```bash
curl http://localhost:8080/health
```

API iş kabul etmeye hazır olduğunda HTTP 200 ve `{"status":"ok"}` döner.

## Ortam

Tüm ayarlar varsayılan değerlere sahiptir; bu sayede konteyner ek yapılandırmaya gerek duymadan çalışır:

| Değişken | Varsayılan | Amaç |
| --- | --- | --- |
| `LATEX_ENGINE` | `tectonic` | LaTeX derlemek için kullanılan ikili (`tectonic`, `lualatex`, vb.). |
| `LATEX_TIMEOUT_SECONDS` | `60` | Derleme çalışmasına izin verilen maksimum saniye. |
| `LATEX_MAIN_FILENAME` | `main.tex` | Yüklenen LaTeX kaynağı kaydedilirken kullanılan hedef dosya adı. |
| `TECTONIC_CACHE_DIR` | `/tmp/tectonic-cache` | Tectonic tarafından indirilen önbelleğe alınmış LaTeX paketlerinin depolama yolu. |

## Sorun Giderme
- Derleme başarısız olduğunda yakalanan derleyici günlüklerini görmek için JSON hata yanıtını inceleyin.
- Gönderilen ZIP dosyalarının çalışma dizininden kaçan yollar içermediğinden emin olun; güvenlik için bu girişler reddedilir.
- Belgeniz yalnızca LuaTeX ile çalışabilen paketlere (ör. `luacode`) bağlıysa `LATEX_ENGINE=lualatex` kullanın.
