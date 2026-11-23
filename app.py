
import streamlit as st
import pandas as pd

from api_client import estimate_api_lambdas
from data_layer import load_matches, available_leagues, available_teams, estimate_lambdas
from engine import analyze_match, fair_odds, expected_value

st.set_page_config(page_title="Independent Odds Engine", page_icon="⚽", layout="wide")

st.title("⚽ Independent Odds Engine 2.0")
st.caption("Bağımsız futbol gol olasılığı ve adil oran motoru")

with st.sidebar:
    st.header("Model ayarı")
    rho = st.slider(
        "Dixon-Coles rho",
        min_value=-0.15,
        max_value=0.15,
        value=0.0,
        step=0.01
    )

    st.divider()
    st.header("Veri merkezi")
    uploaded = st.file_uploader("Geçmiş maç CSV dosyası", type=["csv"])

tab1, tab2 = st.tabs(["Otomatik maç analizi", "CSV geçmiş veri"])

with tab1:
    st.subheader("Maç bilgileri")

    c1, c2 = st.columns(2)

    with c1:
        home = st.text_input("Ev sahibi takım", placeholder="Örn: Bayern Munich")

    with c2:
        away = st.text_input("Deplasman takımı", placeholder="Örn: Hoffenheim")

    if st.button("API ile verileri çek ve analiz et", type="primary"):
        if not home.strip() or not away.strip():
            st.error("İki takımın adını da gir.")
        else:
            try:
                with st.spinner("API-Football verileri alınıyor..."):
                    est = estimate_api_lambdas(home.strip(), away.strip())

                st.session_state["last_est"] = est
                st.session_state["match_name"] = (
                    f'{est["home_name"]} – {est["away_name"]}'
                )
                st.session_state["data_source"] = est["source"]
                st.session_state["data_warning"] = est["warning"]

            except Exception as e:
                st.error(f"Veri alınamadı: {e}")

    if "last_est" in st.session_state:
        est = st.session_state["last_est"]
        result = analyze_match(
            est["lambda_home"],
            est["lambda_away"],
            rho=rho
        )

        st.divider()
        st.subheader(st.session_state["match_name"])

        st.success("API verileri başarıyla işlendi.")

        c1, c2, c3 = st.columns(3)
        c1.metric("Ev sahibi λ", f'{result["lambda_home"]:.2f}')
        c2.metric("Deplasman λ", f'{result["lambda_away"]:.2f}')
        c3.metric("Toplam λ", f'{result["lambda_total"]:.2f}')

        st.caption(
            f'Ev sahibi örneklemi: {est["home_sample"]} maç · '
            f'Deplasman örneklemi: {est["away_sample"]} maç'
        )

        st.warning(est["warning"])

        rows = []
        for line in (0.5, 1.5, 2.5, 3.5, 4.5):
            rows.append({
                "Piyasa": f"{line} Üst",
                "Olasılık": result["over"][line],
                "Adil oran": fair_odds(result["over"][line])
            })
            rows.append({
                "Piyasa": f"{line} Alt",
                "Olasılık": result["under"][line],
                "Adil oran": fair_odds(result["under"][line])
            })

        rows.extend([
            {
                "Piyasa": "KG Var",
                "Olasılık": result["btts_yes"],
                "Adil oran": fair_odds(result["btts_yes"])
            },
            {
                "Piyasa": "KG Yok",
                "Olasılık": result["btts_no"],
                "Adil oran": fair_odds(result["btts_no"])
            }
        ])

        market_df = pd.DataFrame(rows)
        market_df["Olasılık"] = market_df["Olasılık"].map(
            lambda x: f"{x:.1%}"
        )
        market_df["Adil oran"] = market_df["Adil oran"].map(
            lambda x: f"{x:.2f}"
        )

        st.subheader("Bağımsız gol piyasaları")
        st.dataframe(market_df, use_container_width=True, hide_index=True)

        st.subheader("En olası skorlar")
        score_df = pd.DataFrame(
            result["top_scores"],
            columns=["Ev sahibi gol", "Deplasman gol", "Olasılık"]
        )
        score_df["Skor"] = (
            score_df["Ev sahibi gol"].astype(str)
            + "-"
            + score_df["Deplasman gol"].astype(str)
        )
        score_df["Olasılık"] = score_df["Olasılık"].map(
            lambda x: f"{x:.2%}"
        )
        st.dataframe(
            score_df[["Skor", "Olasılık"]],
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Değer analizi")
        st.caption("Bahis oranı yalnızca model sonucu hesaplandıktan sonra girilir.")

        market_names = [
            "0.5 Üst", "1.5 Üst", "2.5 Üst",
            "3.5 Üst", "4.5 Üst", "KG Var", "KG Yok"
        ]
        chosen = st.selectbox("Piyasa", market_names)
        offered = st.number_input(
            "Sunulan bahis oranı",
            min_value=1.01,
            max_value=100.0,
            value=2.00,
            step=0.01
        )

        if chosen.endswith("Üst"):
            line = float(chosen.split()[0])
            prob = result["over"][line]
        elif chosen == "KG Var":
            prob = result["btts_yes"]
        else:
            prob = result["btts_no"]

        ev = expected_value(prob, offered)
        st.metric("Beklenen getiri (EV)", f"{ev:+.1%}")
        st.write(f"Model olasılığı: **{prob:.1%}**")
        st.write(f"Adil oran: **{fair_odds(prob):.2f}**")

with tab2:
    st.subheader("CSV geçmiş veri")

    if uploaded is not None:
        try:
            df = load_matches(uploaded)
            st.success(f"{len(df)} geçerli maç yüklendi.")
            st.dataframe(df.tail(20), use_container_width=True)

        except Exception as e:
            st.error(str(e))
    else:
        st.info("Henüz CSV dosyası yüklenmedi.")
        
