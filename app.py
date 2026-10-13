import os
import json
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
    .info-box {
        background-color: #f3f4f6;
        color: #111827;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)


@st.dialog("Diagnóstico Completo da Partida")
def show_match_summary_dialog(m):
    """Modal com análise rigorosa baseada em Dixon-Coles e dados reais secundários."""
    mkts = m.get("markets", {})
    badges = m.get("ai_badges", [])
    home = m.get("home_team", "")
    away = m.get("away_team", "")
    league = m.get("league", "")
    referee = m.get("referee", "Não divulgado")
    confidence = m.get("data_confidence", "Média")

    g = mkts.get("goals", {})
    exp_gols = g.get("expected_total", 0.0) or 0.0
    
    st.subheader(f"{home} vs {away}")
    st.caption(f"Liga: **{league}** | Árbitro: {referee} | Confiança: {confidence}")

    if badges:
        st.markdown("#### 💡 Parecer Preditivo da IA")
        for b in badges:
            tipo = b.get("tipo")
            texto = b.get("texto", "")
            if tipo == "green": st.success(texto)
            elif tipo == "orange": st.warning(texto)
            elif tipo == "red": st.error(texto)
        st.divider()

    # 1X2
    st.markdown("#### 📊 Probabilidade 1X2 (Matriz Dixon-Coles)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Vitória Casa", f"{g.get('home_win_prob', 0)}%")
    c2.metric("Empate", f"{g.get('draw_prob', 0)}%")
    c3.metric("Vitória Fora", f"{g.get('away_win_prob', 0)}%")
    st.divider()

    st.markdown("#### ⚽ Gols & Mercados Principais")
    col1, col2, col3 = st.columns(3)
    col1.metric("Média Gols", exp_gols)
    col1.metric("+1.5 Gols", f"{g.get('over_1_5', {}).get('prob_over', 0)}%", f"@{g.get('over_1_5', {}).get('fair_odd', 0)}")
    col2.metric("+2.5 Gols", f"{g.get('over_2_5', {}).get('prob_over', 0)}%", f"@{g.get('over_2_5', {}).get('fair_odd', 0)}")
    col2.metric("BTTS (Sim)", f"{g.get('btts', {}).get('prob_yes', 0)}%", f"@{g.get('btts', {}).get('fair_odd', 0)}")
    col3.metric("BTTS ou +2.5", f"{g.get('btts_or_over25', {}).get('prob_hit', 0)}%", f"@{g.get('btts_or_over25', {}).get('fair_odd', 0)}")
    
    st.divider()
    st.markdown("#### 📈 Gols por Time (+1.5)")
    ic1, ic2 = st.columns(2)
    ic1.metric(f"{home} +1.5", f"{g.get('home_over_1_5', {}).get('prob', 0)}%", f"@{g.get('home_over_1_5', {}).get('fair_odd', 0)}")
    ic2.metric(f"{away} +1.5", f"{g.get('away_over_1_5', {}).get('prob', 0)}%", f"@{g.get('away_over_1_5', {}).get('fair_odd', 0)}")


@st.cache_data(ttl=3600)
def load_predictions():
    data_file = os.path.join("data", "predictions_today.json")
    if not os.path.exists(data_file):
        return None
    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)


st.title("⚽ Preditor Quantitativo")

payload = load_predictions()
if payload is None:
    st.warning("Aguardando pipeline. Execute o motor para processar os dados da ESPN.")
    st.stop()

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
    badges = m.get("ai_badges", [])
    home = m.get("home_team", "")
    away = m.get("away_team", "")
    referee = m.get("referee", "Não divulgado")
    conf = m.get("data_confidence", "Média")
    g = mkts.get("goals", {})

    with st.expander(f"{home} vs {away}", expanded=True):
        col_hdr, col_btn = st.columns([3, 1])
        with col_hdr:
            st.markdown(
                f"<span class='badge-league'>{m.get('league')}</span>"
                f"<span class='badge-conf'>Amostra: {conf}</span> | Árbitro: **{referee}**",
                unsafe_allow_html=True
            )
        with col_btn:
            if st.button("📋 Resumo Completo", key=f"btn_pop_{idx}"):
                show_match_summary_dialog(m)

        if badges:
            for b in badges:
                tipo = b.get("tipo")
                texto = b.get("texto", "")
                if tipo == "green": st.success(texto)
                elif tipo == "orange": st.warning(texto)
                elif tipo == "red": st.error(texto)

        # NOVAS ABAS DA FASE 2
        tab_gols, tab_cantos, tab_chutes, tab_cartoes = st.tabs(["⚽ Gols & 1X2", "🚩 Cantos", "🎯 Chutes", "🟨 Cartões"])

        with tab_gols:
            c1, c2, c3 = st.columns(3)
            c1.metric("Vitória Casa", f"{g.get('home_win_prob', 0)}%")
            c2.metric("Empate", f"{g.get('draw_prob', 0)}%")
            c3.metric("Vitória Fora", f"{g.get('away_win_prob', 0)}%")
            
            st.divider()
            st.markdown(f"**Média Esperada de Gols: {g.get('expected_total', 0)}**")
            gc1, gc2 = st.columns(2)
            gc1.metric("+1.5 Gols", f"{g.get('over_1_5', {}).get('prob_over', 0)}%", f"Odd: @{g.get('over_1_5', {}).get('fair_odd', 0)}")
            gc2.metric("+2.5 Gols", f"{g.get('over_2_5', {}).get('prob_over', 0)}%", f"Odd: @{g.get('over_2_5', {}).get('fair_odd', 0)}")
            st.metric("Ambas Marcam (Sim)", f"{g.get('btts', {}).get('prob_yes', 0)}%", f"Odd: @{g.get('btts', {}).get('fair_odd', 0)}")

        with tab_cantos:
            corners = mkts.get("corners", {})
            if corners.get("expected_total") is not None:
                st.metric("Média Esperada de Cantos", corners["expected_total"])
                cc1, cc2, cc3 = st.columns(3)
                cc1.metric("Over 8.5", f"{corners['over_8_5']['prob_over']}%", f"@{corners['over_8_5']['fair_odd']}")
                cc2.metric("Over 9.5", f"{corners['over_9_5']['prob_over']}%", f"@{corners['over_9_5']['fair_odd']}")
                cc3.metric("Over 10.5", f"{corners['over_10_5']['prob_over']}%", f"@{corners['over_10_5']['fair_odd']}")
            else:
                st.info("Dados de cantos em processamento para esta partida.")

        with tab_chutes:
            shots = mkts.get("shots", {})
            if shots.get("expected_total") is not None:
                st.metric("Média Esperada de Chutes no Alvo (Total)", shots["expected_total"])
                sc1, sc2 = st.columns(2)
                sc1.metric("Over 8.5", f"{shots['over_8_5']['prob_over']}%", f"@{shots['over_8_5']['fair_odd']}")
            else:
                st.info("Dados de chutes em processamento para esta partida.")

        with tab_cartoes:
            cards = mkts.get("cards", {})
            if cards.get("expected_total") is not None:
                st.metric("Média Esperada de Cartões (Total)", cards["expected_total"])
                k1, k2 = st.columns(2)
                k1.metric("Over 3.5", f"{cards['over_3_5']['prob_over']}%", f"@{cards['over_3_5']['fair_odd']}")
                k2.metric("Over 4.5", f"{cards['over_4_5']['prob_over']}%", f"@{cards['over_4_5']['fair_odd']}")
            else:
                st.info("Dados de cartões em processamento para esta partida.")