import os
import json
import pandas as pd
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
        font-size: 0.72rem;
        font-weight: 700;
        display: inline-block;
        margin-bottom: 6px;
    }
    .badge-conf {
        background-color: #4b5563;
        color: #f3f4f6;
        padding: 2px 7px;
        border-radius: 4px;
        font-size: 0.68rem;
        font-weight: 600;
        margin-left: 6px;
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

@st.dialog("Diagnóstico Completo da Partida")
def show_match_summary_dialog(m):
    mkts = m.get("markets", {})
    home = m.get("home_team", "")
    away = m.get("away_team", "")
    g = mkts.get("goals", {})
    c = mkts.get("corners", {})
    s = mkts.get("shots", {})
    cd = mkts.get("cards", {})
    combo = g.get("btts_or_over25", {})
    profiles = m.get("team_profiles", {})
    badges = m.get("ai_badges", [])

    st.subheader(f"{home} vs {away}")
    st.caption(f"Liga: {m.get('league')} | Árbitro: {m.get('referee', 'Não divulgado')} | Confiança: {m.get('data_confidence', 'Média')}")

    # --- Dicas da IA no Modal ---
    if badges:
        st.markdown("#### 💡 Parecer Preditivo da IA")
        for b in badges:
            if b.get("tipo") == "green":
                st.success(b.get("texto"))
            elif b.get("tipo") == "orange":
                st.warning(b.get("texto"))
            elif b.get("tipo") == "red":
                st.error(b.get("texto"))
        st.divider()

    st.markdown("#### ⚽ Gols & Mercados Principais")
    col1, col2, col3 = st.columns(3)
    col1.metric("Média Gols", g.get("expected_total", 0))
    col1.metric("+1.5 Gols", f"{g.get('over_1_5', {}).get('prob_over', 0)}%", f"@{g.get('over_1_5', {}).get('fair_odd', 0)}")
    
    col2.metric("+2.5 Gols", f"{g.get('over_2_5', {}).get('prob_over', 0)}%", f"@{g.get('over_2_5', {}).get('fair_odd', 0)}")
    col2.metric("BTTS (Sim)", f"{g.get('btts', {}).get('prob_yes', 0)}%", f"@{g.get('btts', {}).get('fair_odd', 0)}")

    col3.metric("BTTS ou +2.5", f"{combo.get('prob_hit', 0)}%", f"@{combo.get('fair_odd', 0)}")

    st.divider()

    st.markdown("#### 📊 Volume: Cantos, Chutes & Cartões")
    col_v1, col_v2, col_v3 = st.columns(3)
    col_v1.metric("Cantos Totais", c.get("expected_total", 0))
    col_v1.metric("+8.5 Cantos", f"{c.get('over_8_5', {}).get('prob_over', 0)}%", f"@{c.get('over_8_5', {}).get('fair_odd_over', 0)}")

    col_v2.metric("Finalizações", s.get("expected_shots", 0))
    col_v2.metric("+8.5 no Alvo", f"{s.get('over_8_5_sot', {}).get('prob_over', 0)}%", f"@{s.get('over_8_5_sot', {}).get('fair_odd', 0)}")

    col_v3.metric("Cartões Totais", cd.get("expected_total", 0))
    col_v3.metric("+3.5 Cartões", f"{cd.get('over_3_5', {}).get('prob_over', 0)}%", f"@{cd.get('over_3_5', {}).get('fair_odd', 0)}")

    if profiles:
        st.divider()
        st.markdown("#### 📈 Projeção Comparativa por Time")
        h_data = profiles.get("home", {})
        a_data = profiles.get("away", {})
        chart_df = pd.DataFrame({
            "Métrica": ["Finalizações", "No Alvo", "Cantos", "Cartões"],
            f"{home} (Casa)": [h_data.get("shots", 0), h_data.get("sot", 0), h_data.get("corners", 0), h_data.get("cards", 0)],
            f"{away} (Fora)": [a_data.get("shots", 0), a_data.get("sot", 0), a_data.get("corners", 0), a_data.get("cards", 0)],
        }).set_index("Métrica")
        st.bar_chart(chart_df, horizontal=True, stack=False)

st.title("⚽ Preditor Quantitativo")

data_file = os.path.join("data", "predictions_today.json")
if not os.path.exists(data_file):
    st.warning("Aguardando pipeline. Execute o motor para gerar dados.")
    st.stop()

with open(data_file, "r", encoding="utf-8") as f:
    payload = json.load(f)

# Blindagem: suporta tanto dicionário envelopado quanto lista direta de jogos
if isinstance(payload, dict):
    shift = payload.get("shift", "").upper()
    updated = payload.get("updated_at", "")[:16].replace("T", " ")
    matches = payload.get("matches", [])
else:
    shift = "RODADA DIÁRIA"
    updated = "Hoje"
    matches = payload if isinstance(payload, list) else []

st.caption(f"Turno: **{shift}** | Atualizado em: {updated}")

if not matches:
    st.info("Nenhuma partida agendada para este ciclo.")
    st.stop()

leagues = sorted(list({m.get("league", "") for m in matches if m.get("league")}))
selected_league = st.selectbox("Filtrar Liga", ["Todas"] + leagues)

filtered = [m for m in matches if selected_league == "Todas" or m.get("league") == selected_league]

for idx, m in enumerate(filtered):
    mkts = m.get("markets", {})
    home = m.get("home_team", "")
    away = m.get("away_team", "")
    referee = m.get("referee", "Não divulgado")
    conf = m.get("data_confidence", "Média")
    profiles = m.get("team_profiles", {})
    badges = m.get("ai_badges", [])

    with st.expander(f"{home} vs {away}", expanded=True):
        col_hdr, col_btn = st.columns([3, 1])
        with col_hdr:
            st.markdown(
                f"<span class='badge-league'>{m.get('league')}</span> "
                f"<span class='badge-conf'>Amostra: {conf}</span> | Árbitro: **{referee}**",
                unsafe_allow_html=True
            )
        with col_btn:
            if st.button("📋 Resumo (Print)", key=f"btn_pop_{idx}"):
                show_match_summary_dialog(m)

        # --- Dicas da IA no Card Principal ---
        if badges:
            for b in badges:
                if b.get("tipo") == "green":
                    st.success(b.get("texto"))
                elif b.get("tipo") == "orange":
                    st.warning(b.get("texto"))
                elif b.get("tipo") == "red":
                    st.error(b.get("texto"))

        tab_gols, tab_combo, tab_grafico, tab_cantos, tab_chutes, tab_cards = st.tabs([
            "Gols", "BTTS ou +2.5", "Comparativo 📊", "Cantos", "Chutes", "Cartões"
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
            if prob_combo >= 75.0:
                st.markdown("<span class='badge-value'>SINAL QUANTITATIVO: ALTA PROBABILIDADE</span>", unsafe_allow_html=True)
            st.metric("Ambas Marcam OU +2.5 Gols", f"{prob_combo}%", f"Odd Justa: @{combo.get('fair_odd', 0)}")
            st.caption("Critério: Placar diferente de 0-0, 1-0, 2-0, 0-1 ou 0-2.")

        with tab_grafico:
            if profiles:
                h_data = profiles.get("home", {})
                a_data = profiles.get("away", {})
                chart_df = pd.DataFrame({
                    "Métrica": ["Finalizações", "Chutes no Alvo", "Escanteios", "Cartões"],
                    f"{home} (Casa)": [h_data.get("shots", 0), h_data.get("sot", 0), h_data.get("corners", 0), h_data.get("cards", 0)],
                    f"{away} (Fora)": [a_data.get("shots", 0), a_data.get("sot", 0), a_data.get("corners", 0), a_data.get("cards", 0)],
                }).set_index("Métrica")
                st.write("**Projeção Volumétrica por Equipe:**")
                st.bar_chart(chart_df, horizontal=True, stack=False)
            else:
                st.info("Dados de perfil individual não disponíveis para esta partida.")

        with tab_cantos:
            c = mkts.get("corners", {})
            st.write(f"Média Esperada: **{c.get('expected_total', 0)} cantos**")
            
            # Médias individuais por mando
            if profiles:
                h_c = profiles.get("home", {}).get("corners", 0)
                a_c = profiles.get("away", {}).get("corners", 0)
                st.caption(f"🚩 **{home} (Casa):** ~{h_c} cantos | **{away} (Fora):** ~{a_c} cantos")

            c1, c2 = st.columns(2)
            c1.metric("+8.5 Cantos", f"{c.get('over_8_5', {}).get('prob_over', 0)}%", f"Odd: @{c.get('over_8_5', {}).get('fair_odd_over', 0)}")
            c2.metric("+10.5 Cantos", f"{c.get('over_10_5', {}).get('prob_over', 0)}%", f"Odd: @{c.get('over_10_5', {}).get('fair_odd', 0)}")

        with tab_chutes:
            s = mkts.get("shots", {})
            st.metric("Finalizações Totais Esperadas", s.get("expected_shots", 0))
            sot = s.get("over_8_5_sot", {})
            st.metric("+8.5 Chutes no Alvo", f"{sot.get('prob_over', 0)}%", f"Odd: @{sot.get('fair_odd', 0)}")

        with tab_cards:
            cd = mkts.get("cards", {})
            st.write(f"Fator Árbitro: **{cd.get('referee_factor', 1.0)}x** | Média Esperada: **{cd.get('expected_total', 0)}**")
            
            # Médias individuais de cartões por mando
            if profiles:
                h_cd = profiles.get("home", {}).get("cards", 0)
                a_cd = profiles.get("away", {}).get("cards", 0)
                st.caption(f"🟨 **{home} (Casa):** ~{h_cd} cartões | **{away} (Fora):** ~{a_cd} cartões")

            c1, c2 = st.columns(2)
            c1.metric("+3.5 Cartões", f"{cd.get('over_3_5', {}).get('prob_over', 0)}%", f"Odd: @{cd.get('over_3_5', {}).get('fair_odd', 0)}")
            c2.metric("+4.5 Cartões", f"{cd.get('over_4_5', {}).get('prob_over', 0)}%", f"Odd: @{cd.get('over_4_5', {}).get('fair_odd', 0)}")