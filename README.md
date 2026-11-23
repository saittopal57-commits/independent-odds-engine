# Independent Odds Engine 1.0

Bağımsız futbol gol olasılığı ve adil oran hesaplama MVP'si.

## Özellikler
- CSV geçmiş maç verisi yükleme
- İsteğe bağlı xG / xGA sütunlarını kullanma
- Lig ortalamasına doğru daraltılmış takım hücum/savunma oranları
- Poisson gol dağılımı
- Opsiyonel Dixon-Coles düşük skor düzeltmesi
- 0.5–4.5 Alt/Üst, KG Var/Yok, en olası skorlar
- Sunulan fiyat girildiğinde tahmin sonrası EV analizi

## Kurulum
Python 3.10+ önerilir.

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Uygulama tarayıcıda açılır. Android telefondan kullanmak için uygulamayı Streamlit Community Cloud veya başka bir sunucuya dağıtmak gerekir.

## CSV formatı
Zorunlu sütunlar:
`date, league, home_team, away_team, home_goals, away_goals`

İsteğe bağlı:
`home_xg, away_xg`

Tarih örneği: `2026-08-01`

Örnek satır:
`2026-08-01,Premier League,Arsenal,Chelsea,2,1,1.8,0.9`

## Veri kaynağı notu
Bu paket canlı API'ye bağlanmaz ve internetten kendiliğinden veri çektiğini iddia etmez. İlk aşamada CSV/manuel veri ile çalışır. Otomatik katman için lisans ve kullanım koşulları uygun bir futbol veri sağlayıcısı seçilip API anahtarı güvenli biçimde sunucu ortam değişkenine eklenmelidir.

## Önemli metodolojik not
- Bahis şirketi oranları tahmin üretiminde kullanılmaz.
- Sunulan oran yalnızca tahmin sonrasında beklenen değer hesabına girer.
- Model henüz geçmiş veri üzerinde kalibre edilmiş değildir.
- EV, model olasılığının doğru olduğu varsayımı altında hesaplanır; garanti veya kesin kazanç göstergesi değildir.
- Takım formülü MVP seviyesindedir; lig/ev-deplasman etkileri, rakip gücü ve xG kapsamı daha geniş tarihsel veriyle geliştirilmelidir.
