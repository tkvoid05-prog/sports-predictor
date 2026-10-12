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
    .badge-dna {
        background-color: #374151;
        color: #e5e7eb;
        padding: 2px 7px;
        border-radius: 4px;
        font-size: 0.70rem;
        font-weight: 600;
        margin-left: 6px;
        border: 1px solid #4b5563;
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
    """Modal com análise rigorosa baseada em Dixon-Coles."""
    mkts = m.get("markets", {})
    badges = m.get("ai_badges", [])
    home = m.get("home_team", "")
    away = m.get("away_team", "")
    league = m.get("league", "")
    referee = m.get("referee", "Não divulgado")
    confidence = m.get("data_confidence", "Média")

    g = mkts.get("goals", {})
    exp_gols = g.get("expected_total", 0.0) or 0.0
    p_o15 = g.get("over_1_5", {}).get("prob_over", 0.0) or 0.0
    odd_o15 = g.get("over_1_5", {}).get("fair_odd", 0.0) or 0.0
    p_o25 = g.get("over_2_5", {}).get("prob_over", 0.0) or 0.0
    odd_o25 = g.get("over_2_5", {}).get("fair_odd", 0.0) or 0.0
    p_btts = g.get("btts", {}).get("prob_yes", 0.0) or 0.0
    odd_btts = g.get("btts", {}).get("fair_odd", 0.0) or 0.0

    combo = g.get("btts_or_over25", {})
    prob_combo = combo.get("prob_hit", 0.0) or 0.0
    fair_odd_combo = combo.get("fair_odd", 0.0) or 0.0

    st.subheader(f"{home} vs {away}")
    st.caption(f"Liga: **{league}** | Árbitro: {referee} | Confiança: {confidence}")

    if badges:
        st.markdown("#### 💡 Parecer Preditivo da IA")
        for b in badges:
            tipo = b.get("tipo")
            texto = b.get("texto", "")
            if tipo == "green":
                st.success(texto)
            elif tipo == "orange":
                st.warning(texto)
            elif tipo == "red":
                st.error(texto)
        st.divider()

    st.markdown("#### ⚽ Gols & Mercados Principais (Dixon-Coles)")
    col1, col2, col3 = st.columns(3)
    col1.metric("Média Gols", exp_gols)
    col1.metric("+1.5 Gols", f"{p_o15}%", f"@{odd_o15}")
    col2.metric("+2.5 Gols", f"{p_o25}%", f"@{odd_o25}")
    col2.metric("BTTS (Sim)", f"{p_btts}%", f"@{odd_btts}")
    col3.metric("BTTS ou +2.5", f"{prob_combo}%", f"@{fair_odd_combo}")

    st.divider()
    st.markdown(
        "<div class='info-box'>"
        "<strong>Nota Arquitetural:</strong> Mercados de Cantos, Chutes e Cartões estão temporariamente "
        "desativados (Fase 2) para garantir 100% de precisão estatística baseada em dados reais da ESPN."
        "</div>",
        unsafe_allow_html=True
    )


@st.cache_data(ttl=3600)
def load_predictions():
    """Carrega o JSON com cache de memória para evitar I/O repetitivo."""
    data_file = os.path.join("data", "predictions_today.json")
    if not os.path.exists(data_file):
        return None
    with open(data_file, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload


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
    exp_gols = g.get("expected_total", 0.0) or 0.0
    p_o15 = g.get("over_1_5", {}).get("prob_over", 0.0) or 0.0
    odd_o15 = g.get("over_1_5", {}).get("fair_odd", 0.0) or 0.0
    p_o25 = g.get("over_2_5", {}).get("prob_over", 0.0) or 0.0
    odd_o25 = g.get("over_2_5", {}).get("fair_odd", 0.0) or 0.0
    p_btts = g.get("btts", {}).get("prob_yes", 0.0) or 0.0
    odd_btts = g.get("btts", {}).get("fair_odd", 0.0) or 0.0

    combo = g.get("btts_or_over25", {})
    prob_combo = combo.get("prob_hit", 0.0) or 0.0
    fair_odd_combo = combo.get("fair_odd", 0.0) or 0.0

    with st.expander(f"{home} vs {away}", expanded=True):
        col_hdr, col_btn = st.columns([3, 1])
        with col_hdr:
            st.markdown(
                f"<span class='badge-league'>{m.get('league')}</span>"
                f"<span class='badge-conf'>Amostra: {conf}</span> | Árbitro: **{referee}**",
                unsafe_allow_html=True
            )
        with col_btn:
            if st.button("📋 Resumo (Print)", key=f"btn_pop_{idx}"):
                show_match_summary_dialog(m)

        if badges:
            for b in badges:
                tipo = b.get("tipo")
                texto = b.get("texto", "")
                if tipo == "green":
                    st.success(texto)
                elif tipo == "orange":
                    st.warning(texto)
                elif tipo == "red":
                    st.error(texto)

        tab_gols, tab_combo = st.tabs(["Gols", "BTTS ou +2.5"])

        with tab_gols:
            st.write(f"Média Esperada de Gols: **{exp_gols}**")
            c1, c2 = st.columns(2)
            c1.metric("+1.5 Gols", f"{p_o15}%", f"Odd Justa: @{odd_o15}")
            c2.metric("+2.5 Gols", f"{p_o25}%", f"Odd Justa: @{odd_o25}")
            st.metric("Ambas Marcam (Sim)", f"{p_btts}%", f"Odd Justa: @{odd_btts}")

        with tab_combo:
            if prob_combo >= 75.0:
                st.markdown("<span class='badge-value'>SINAL QUANTITATIVO: ALTA PROBABILIDADE</span>", unsafe_allow_html=True)
            st.metric("Ambas Marcam OU +2.5 Gols", f"{prob_combo}%", f"Odd Justa: @{fair_odd_combo}")
            st.caption("Critério: Placar diferente de 0-0, 1-0, 2-0, 0-1 ou 0-2.")

        st.markdown(
            "<div class='info-box'>"
            "<strong>Nota Arquitetural:</strong> Mercados de Cantos, Chutes e Cartões estão temporariamente "
            "desativados (Fase 2) para garantir 100% de precisão estatística baseada em dados reais da ESPN."
            "</div>",
            unsafe_allow_html=True
        )