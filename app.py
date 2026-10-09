import json
import os
import streamlit as st

st.set_page_config(
    page_title="Preditor Esportivo",
    page_icon="⚽",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Estilização compacta para tela de celular
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .metric-card {
        background-color: #1e293b;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 8px;
        border: 1px solid #334155;
    }
    .badge {
        background-color: #2563eb;
        color: white;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("⚽ Preditor Esportivo")

data_file = os.path.join("data", "predictions_today.json")

if not os.path.exists(data_file):
    st.warning("Nenhum dado processado ainda. Execute o pipeline primeiro.")
    st.stop()

with open(data_file, "r", encoding="utf-8") as f:
    payload = json.load(f)

shift = payload.get("shift", "").upper()
updated = payload.get("updated_at", "")[:16].replace("T", " ")
matches = payload.get("matches", [])

st.caption(f"Turno: **{shift}** | Atualizado em: {updated}")

if not matches:
    st.info("Nenhuma partida agendada para este turno.")
    st.stop()

# Filtro por liga
leagues = sorted(list({m.get("league", "") for m in matches if m.get("league")}))
selected_league = st.selectbox("Selecione a Liga", ["Todas"] + leagues)

filtered = [
    m
    for m in matches
    if selected_league == "Todas" or m.get("league") == selected_league
]

for m in filtered:
    mkts = m.get("markets", {})
    home = m.get("home_team", "")
    away = m.get("away_team", "")
    referee = m.get("referee", "Não divulgado")

    with st.expander(f"{home} vs {away}", expanded=True):
        st.markdown(
            f"<span class='badge'>{m.get('league')}</span> | Árbitro: **{referee}**",
            unsafe_allow_html=True,
        )

        tab_gols, tab_cantos, tab_chutes, tab_faltas, tab_cards = st.tabs(
            ["Gols", "Cantos", "Chutes", "Faltas", "Cartões"]
        )

        with tab_gols:
            g = mkts.get("goals", {})
            st.write(f"Média Esperada de Gols: **{g.get('expected_total', 0)}**")
            col1, col2 = st.columns(2)
            col1.metric(
                "+1.5 Gols", f"{g.get('over_1_5', {}).get('prob_over', 0)}%"
            )
            col2.metric(
                "+2.5 Gols", f"{g.get('over_2_5', {}).get('prob_over', 0)}%"
            )

        with tab_cantos:
            c = mkts.get("corners", {})
            st.write(
                f"Média Esperada de Escanteios: **{c.get('expected_total', 0)}**"
            )
            col1, col2 = st.columns(2)
            col1.metric(
                "+8.5 Cantos", f"{c.get('over_8_5', {}).get('prob_over', 0)}%"
            )
            col2.metric(
                "+10.5 Cantos",
                f"{c.get('over_10_5', {}).get('prob_over', 0)}%",
            )

        with tab_chutes:
            s = mkts.get("shots", {})
            col1, col2 = st.columns(2)
            col1.metric("Chutes Totais", s.get("expected_shots", 0))
            col2.metric(
                "+24.5 Chutes",
                f"{s.get('over_24_5_shots', {}).get('prob_over', 0)}%",
            )

        with tab_faltas:
            f_m = mkts.get("fouls", {})
            st.write(
                f"Média Esperada de Faltas: **{f_m.get('expected_total', 0)}**"
            )
            st.metric(
                "+25.5 Faltas",
                f"{f_m.get('over_25_5', {}).get('prob_over', 0)}%",
            )

        with tab_cards:
            cd = mkts.get("cards", {})
            st.write(
                f"Fator de Rigor do Árbitro: **{cd.get('referee_factor', 1.0)}x**"
            )
            col1, col2 = st.columns(2)
            col1.metric(
                "+3.5 Cartões", f"{cd.get('over_3_5', {}).get('prob_over', 0)}%"
            )
            col2.metric(
                "+4.5 Cartões", f"{cd.get('over_4_5', {}).get('prob_over', 0)}%"
            )