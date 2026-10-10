import json
import os
import streamlit as st

st.set_page_config(page_title="Preditor Quant", page_icon="⚽", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    .badge-value {
        background-color: #059669;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        display: inline-block;
        margin-bottom: 6px;
    }
    .badge-league {
        background-color: #2563eb;
        color: white;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚽ Preditor Quantitativo")

data_file = os.path.join("data", "predictions_today.json")
if not os.path.exists(data_file):
    st.warning("Aguardando geração da base. Execute o pipeline primeiro.")
    st.stop()

with open(data_file, "r", encoding="utf-8") as f:
    payload = json.load(f)

shift = payload.get("shift", "").upper()
updated = payload.get("updated_at", "")[:16].replace("T", " ")
matches = payload.get("matches", [])

st.caption(f"Turno: **{shift}** | Atualizado em: {updated}")

if not matches:
    st.info("Nenhuma partida programada para este ciclo.")
    st.stop()

leagues = sorted(list({m.get("league", "") for m in matches if m.get("league")}))
selected_league = st.selectbox("Filtrar Liga", ["Todas"] + leagues)

filtered = [m for m in matches if selected_league == "Todas" or m.get("league") == selected_league]

for m in filtered:
    mkts = m.get("markets", {})
    home = m.get("home_team", "")
    away = m.get("away_team", "")
    referee = m.get("referee", "Não divulgado")

    with st.expander(f"{home} vs {away}", expanded=True):
        st.markdown(f"<span class='badge-league'>{m.get('league')}</span> | Árbitro: **{referee}**", unsafe_allow_html=True)

        tab_gols, tab_combo, tab_cantos, tab_chutes, tab_cards = st.tabs([
            "Gols", "BTTS ou +2.5", "Cantos", "Chutes", "Cartões"
        ])

        with tab_gols:
            g = mkts.get("goals", {})
            st.write(f"Média Esperada de Gols: **{g.get('expected_total', 0)}**")
            c1, c2 = st.columns(2)
            c1.metric("+1.5 Gols", f"{g.get('over_1_5', {}).get('prob_over', 0)}%", f"Odd Justa: @{g.get('over_1_5', {}).get('fair_odd', 0)}")
            c2.metric("+2.5 Gols", f"{g.get('over_2_5', {}).get('prob_over', 0)}%", f"Odd Justa: @{g.get('over_2_5', {}).get('fair_odd', 0)}")
            st.metric("Ambas Marcam (Sim)", f"{g.get('btts', {}).get('prob_yes', 0)}%", f"Odd Justa: @{g.get('btts', {}).get('fair_odd', 0)}")

        with tab_combo:
            combo = mkts.get("goals", {}).get("btts_or_over25", {})
            prob_combo = combo.get("prob_hit", 0)
            if prob_combo >= 70.0:
                st.markdown("<span class='badge-value'>ALTA PROBABILIDADE HISTÓRICA</span>", unsafe_allow_html=True)
            st.metric("Ambas Marcam OU +2.5 Gols", f"{prob_combo}%", f"Odd Justa: @{combo.get('fair_odd', 0)}")
            st.caption("Perde apenas se o placar terminar em 0-0, 1-0, 2-0, 0-1 ou 0-2.")

        with tab_cantos:
            c = mkts.get("corners", {})
            st.write(f"Média Esperada: **{c.get('expected_total', 0)} cantos**")
            c1, c2 = st.columns(2)
            c1.metric("+8.5 Cantos", f"{c.get('over_8_5', {}).get('prob_over', 0)}%", f"Odd: @{c.get('over_8_5', {}).get('fair_odd_over', 0)}")
            c2.metric("+10.5 Cantos", f"{c.get('over_10_5', {}).get('prob_over', 0)}%", f"Odd: @{c.get('over_10_5', {}).get('fair_odd_over', 0)}")

        with tab_chutes:
            s = mkts.get("shots", {})
            st.metric("Finalizações Esperadas", s.get("expected_shots", 0))
            sot = s.get("over_8_5_sot", {})
            st.metric("+8.5 Chutes no Alvo", f"{sot.get('prob_over', 0)}%", f"Odd: @{sot.get('fair_odd', 0)}")

        with tab_cards:
            cd = mkts.get("cards", {})
            st.write(f"Fator Árbitro: **{cd.get('referee_factor', 1.0)}x** | Média Esperada: **{cd.get('expected_total', 0)}**")
            c1, c2 = st.columns(2)
            c1.metric("+3.5 Cartões", f"{cd.get('over_3_5', {}).get('prob_over', 0)}%", f"Odd: @{cd.get('over_3_5', {}).get('fair_odd', 0)}")
            c2.metric("+4.5 Cartões", f"{cd.get('over_4_5', {}).get('prob_over', 0)}%", f"Odd: @{cd.get('over_4_5', {}).get('fair_odd', 0)}")