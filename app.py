import streamlit as st
import pandas as pd
from data_layer import load_matches, available_leagues, available_teams, estimate_lambdas
from engine import analyze_match, fair_odds, expected_value

st.set_page_config(page_title="Independent Odds Engine", page_icon="⚽", layout="wide")
st.title("⚽ Independent Odds Engine 1.0")
st.caption("Bağımsız futbol gol olasılığı ve adil oran motoru · Tahmin motorunda bahis şirketi oranı kullanılmaz.")

st.info("Bu sürüm MVP'dir. CSV geçmiş maç verisi veya manuel gol beklentisiyle çalışır. Otomatik canlı veri sağlayıcısı bağlantısı henüz eklenmemiştir.")

with st.sidebar:
    st.header("Veri merkezi")
    uploaded = st.file_uploader("Geçmiş maç CSV dosyası yükle", type=["csv"])
    st.caption("Şablon: date, league, home_team, away_team, home_goals, away_goals. home_xg ve away_xg isteğe bağlı.")
    st.divider()
    st.header("Model ayarı")
    rho = st.slider("Dixon-Coles rho", min_value=-0.15, max_value=0.15, value=0.0, step=0.01)
    st.caption("İlk testlerde 0 bırak. Rho, geçmiş veriden kalibre edilmeden avantaj sağlamaz.")

df = None
if uploaded is not None:
    try:
        df = load_matches(uploaded)
        st.success(f"{len(df)} geçerli maç yüklendi.")
    except Exception as e:
        st.error(str(e))

tab1, tab2, tab3 = st.tabs(["Maç analizi", "Veri kontrolü", "Model hakkında"])

with tab1:
    st.subheader("Maç seçimi")
    use_history = df is not None and len(df) > 0
    if use_history:
        leagues = available_leagues(df)
        league = st.selectbox("Lig", leagues)
        teams = available_teams(df, league)
        c1, c2 = st.columns(2)
        with c1:
            home = st.selectbox("Ev sahibi", teams, index=0)
        with c2:
            away_options = [t for t in teams if t != home]
            away = st.selectbox("Deplasman", away_options)
        if st.button("Geçmiş veriden gol beklentisi hesapla", type="primary"):
            try:
                est = estimate_lambdas(df, league, home, away)
                st.session_state["last_est"] = est
                st.session_state["match_name"] = f"{home} – {away}"
                st.session_state["league_name"] = league
            except Exception as e:
                st.error(str(e))
    else:
        st.warning("CSV yüklemediğin için manuel moddasın. Otomatik istatistik tahmini için geçmiş maç dosyası gerekir.")
        c1, c2 = st.columns(2)
        with c1:
            home = st.text_input("Ev sahibi takım", "Ev Sahibi")
            lh = st.number_input("Ev sahibi gol beklentisi (λ)", 0.05, 5.0, 1.45, 0.05)
        with c2:
            away = st.text_input("Deplasman takımı", "Deplasman")
            la = st.number_input("Deplasman gol beklentisi (λ)", 0.05, 5.0, 1.10, 0.05)
        if st.button("Maçı analiz et", type="primary"):
            st.session_state["last_est"] = {"lambda_home": lh, "lambda_away": la}
            st.session_state["match_name"] = f"{home} – {away}"
            st.session_state["league_name"] = "Manuel giriş"

    if "last_est" in st.session_state:
        est = st.session_state["last_est"]
        name = st.session_state.get("match_name", "Seçilen maç")
        result = analyze_match(est["lambda_home"], est["lambda_away"], rho=rho)
        st.divider()
        st.subheader(name)
        c1, c2, c3 = st.columns(3)
        c1.metric("Ev sahibi gol beklentisi", f'{result["lambda_home"]:.2f}')
        c2.metric("Deplasman gol beklentisi", f'{result["lambda_away"]:.2f}')
        c3.metric("Toplam gol beklentisi", f'{result["lambda_total"]:.2f}')

        rows = []
        for line in (0.5, 1.5, 2.5, 3.5, 4.5):
            p_over = result["over"][line]
            p_under = result["under"][line]
            rows.extend([
                {"Piyasa": f"{line} Üst", "Olasılık": p_over, "Adil oran": fair_odds(p_over)},
                {"Piyasa": f"{line} Alt", "Olasılık": p_under, "Adil oran": fair_odds(p_under)},
            ])
        rows.extend([
            {"Piyasa": "KG Var", "Olasılık": result["btts_yes"], "Adil oran": fair_odds(result["btts_yes"])},
            {"Piyasa": "KG Yok", "Olasılık": result["btts_no"], "Adil oran": fair_odds(result["btts_no"])},
        ])
        market_df = pd.DataFrame(rows)
        market_df["Olasılık"] = market_df["Olasılık"].map(lambda x: f"{x:.1%}")
        market_df["Adil oran"] = market_df["Adil oran"].map(lambda x: f"{x:.2f}")
        st.subheader("Bağımsız gol piyasaları")
        st.dataframe(market_df, use_container_width=True, hide_index=True)

        st.subheader("En olası skorlar")
        score_df = pd.DataFrame(result["top_scores"], columns=["Ev sahibi gol", "Deplasman gol", "Olasılık"])
        score_df["Skor"] = score_df["Ev sahibi gol"].astype(str) + "-" + score_df["Deplasman gol"].astype(str)
        score_df["Olasılık"] = score_df["Olasılık"].map(lambda x: f"{x:.2%}")
        st.dataframe(score_df[["Skor", "Olasılık"]], use_container_width=True, hide_index=True)

        st.subheader("Değer analizi (isteğe bağlı)")
        st.caption("Bu alana sunulan bahis fiyatını gir. Bu fiyat tahmin ve adil oran hesabını değiştirmez.")
        market_names = ["0.5 Üst", "1.5 Üst", "2.5 Üst", "3.5 Üst", "4.5 Üst", "KG Var", "KG Yok"]
        chosen = st.selectbox("Karşılaştırılacak piyasa", market_names)
        offered = st.number_input("Sunulan oran", min_value=1.01, max_value=100.0, value=2.00, step=0.01)
        if chosen.endswith("Üst"):
            line = float(chosen.split()[0])
            prob = result["over"][line]
        elif chosen == "KG Var":
            prob = result["btts_yes"]
        else:
            prob = result["btts_no"]
        ev = expected_value(prob, offered)
        st.metric("Modelin beklenen getirisi (EV)", f"{ev:+.1%}")
        st.write(f"Model olasılığı: **{prob:.1%}** · Adil oran: **{fair_odds(prob):.2f}**")
        if ev > 0:
            st.success("Girilen fiyat, modelin adil oranından yüksek. Bu yalnızca model varsayımına dayalı matematiksel avantajdır; garanti değildir.")
        else:
            st.warning("Girilen fiyat, modelin hesapladığı adil oran seviyesinin altında.")

with tab2:
    st.subheader("Yüklenen veri özeti")
    if df is not None:
        st.write(f"Toplam geçerli maç: **{len(df)}**")
        st.write("Lig başına maç sayısı")
        st.dataframe(df.groupby("league").size().rename("Maç sayısı").reset_index(), hide_index=True)
        st.dataframe(df.tail(20), use_container_width=True, hide_index=True)
    else:
        st.write("Henüz CSV yüklenmedi.")
    st.download_button("CSV şablonunu indir", data="date,league,home_team,away_team,home_goals,away_goals,home_xg,away_xg\n2026-08-01,Premier League,Team A,Team B,2,1,1.7,0.9\n", file_name="independent_odds_template.csv", mime="text/csv")

with tab3:
    st.subheader("Model sınırları ve sonraki geliştirmeler")
    st.markdown("""
- Mevcut veri katmanı CSV geçmiş maç verisini okur; otomatik sağlayıcı entegrasyonu henüz bağlı değildir.
- xG sütunları varsa gol ve xG ölçümleri kontrollü biçimde harmanlanır.
- Takım oranları küçük örneklemlerde lig ortalamasına doğru daraltılır.
- İlk sürüm skor olasılıkları için Poisson, opsiyonel düşük skor düzeltmesi için Dixon-Coles kullanır.
- İlk yarı tahmini, ilk yarı verisi ve ayrı bir model olmadan üretilmez.
- Korner ve kart piyasaları bu sürümün kapsamı dışındadır.
- Model geçmiş veride zaman sıralı test ve kalibrasyon yapılmadan bahis kararı için güvenilir kabul edilmemelidir.
""")
