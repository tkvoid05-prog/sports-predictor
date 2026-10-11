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
    </style>
""", unsafe_allow_html=True)

def resolve_league_dna(m):
    if m.get("league_dna"):
        return m.get("league_dna")
    lg = m.get("league", "").lower()
    if "premier league" in lg:
        return "⚡ Ritmo Alto | 🚩 +Cantos | 🟨 -Cartões"
    elif "brasileir" in lg:
        return "🛑 Jogo Picardado | 🟨 +Cartões | ⏱️ Ritmo Médio"
    elif "la liga" in lg:
        return "🎯 Posse Cadenciada | 🟨 +Cartões"
    return "⚖️ Padrão Equilibrado"

@st.dialog("Diagnóstico Completo da Partida")
def show_match_summary_dialog(m):
    mkts = m.get("markets", {})
    probs = m.get("probabilities", {})
    ind = m.get("stats_individual", {})
    profiles = m.get("team_profiles", {})
    badges = m.get("ai_badges", [])
    home = m.get("home_team", "")
    away = m.get("away_team", "")
    dna = resolve_league_dna(m)

    # Gols
    g = mkts.get("goals", {})
    exp_gols = g.get("expected_total", probs.get("exp_total_goals", 0))
    p_o15 = g.get("over_1_5", {}).get("prob_over", probs.get("prob_over_15", 0))
    odd_o15 = g.get("over_1_5", {}).get("fair_odd", probs.get("odd_over_15", 0))
    p_o25 = g.get("over_2_5", {}).get("prob_over", probs.get("prob_over_25", 0))
    odd_o25 = g.get("over_2_5", {}).get("fair_odd", probs.get("odd_over_25", 0))
    p_btts = g.get("btts", {}).get("prob_yes", probs.get("prob_btts", 0))
    odd_btts = g.get("btts", {}).get("fair_odd", probs.get("odd_btts", 0))

    # Combo BTTS ou +2.5
    combo = g.get("btts_or_over25", {})
    prob_combo = combo.get("prob_hit", 0)
    fair_odd_combo = combo.get("fair_odd", 0)
    if prob_combo == 0 and (p_btts > 0 or p_o25 > 0):
        prob_combo = round(min(95.0, max(p_btts, p_o25) + 12.0), 1)
        fair_odd_combo = round(100.0 / prob_combo, 2) if prob_combo > 0 else 0

    # Cantos
    c = mkts.get("corners", {})
    exp_cantos = c.get("expected_total", ind.get("corners_total", 9.5))
    p_c85 = c.get("over_8_5", {}).get("prob_over", 0)
    odd_c85 = c.get("over_8_5", {}).get("fair_odd_over", 0)
    if p_c85 == 0 and exp_cantos > 0:
        p_c85 = round(min(92.0, max(45.0, (exp_cantos / 9.5) * 65.0)), 1)
        odd_c85 = round(100.0 / p_c85, 2) if p_c85 > 0 else 0

    # Chutes
    s = mkts.get("shots", {})
    exp_shots = s.get("expected_shots", 0)
    p_sot = s.get("over_8_5_sot", {}).get("prob_over", 0)
    odd_sot = s.get("over_8_5_sot", {}).get("fair_odd", 0)
    if exp_shots == 0 and exp_gols > 0:
        exp_shots = round(exp_gols * 9.5 + 4.0, 1)
        p_sot = round(min(88.0, max(40.0, (exp_shots / 24.0) * 62.0)), 1)
        odd_sot = round(100.0 / p_sot, 2) if p_sot > 0 else 0

    # Cartões
    cd = mkts.get("cards", {})
    exp_cards = cd.get("expected_total", ind.get("cards_total", 4.5))
    p_cd35 = cd.get("over_3_5", {}).get("prob_over", 0)
    odd_cd35 = cd.get("over_3_5", {}).get("fair_odd", 0)
    if p_cd35 == 0 and exp_cards > 0:
        p_cd35 = round(min(92.0, max(45.0, (exp_cards / 4.5) * 68.0)), 1)
        odd_cd35 = round(100.0 / p_cd35, 2) if p_cd35 > 0 else 0

    st.subheader(f"{home} vs {away}")
    st.caption(f"Liga: **{m.get('league')}** | Perfil: `{dna}` | Árbitro: {m.get('referee', 'Não divulgado')} | Confiança: {m.get('data_confidence', 'Média')}")

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
    col1.metric("Média Gols", exp_gols)
    col1.metric("+1.5 Gols", f"{p_o15}%", f"@{odd_o15}")
    col2.metric("+2.5 Gols", f"{p_o25}%", f"@{odd_o25}")
    col2.metric("BTTS (Sim)", f"{p_btts}%", f"@{odd_btts}")
    col3.metric("BTTS ou +2.5", f"{prob_combo}%", f"@{fair_odd_combo}")

    st.divider()

    st.markdown("#### 📊 Volume: Cantos, Chutes & Cartões")
    col_v1, col_v2, col_v3 = st.columns(3)
    col_v1.metric("Cantos Totais", exp_cantos)
    col_v1.metric("+8.5 Cantos", f"{p_c85}%", f"@{odd_c85}")
    col_v2.metric("Finalizações", exp_shots)
    col_v2.metric("+8.5 no Alvo", f"{p_sot}%", f"@{odd_sot}")
    col_v3.metric("Cartões Totais", exp_cards)
    col_v3.metric("+3.5 Cartões", f"{p_cd35}%", f"@{odd_cd35}")

    h_shots = profiles.get("home", {}).get("shots", round(exp_shots * 0.55, 1))
    a_shots = profiles.get("away", {}).get("shots", round(exp_shots * 0.45, 1))
    h_sot = profiles.get("home", {}).get("sot", round(h_shots * 0.35, 1))
    a_sot = profiles.get("away", {}).get("sot", round(a_shots * 0.35, 1))
    h_cantos = profiles.get("home", {}).get("corners", ind.get("corners_home", round(exp_cantos * 0.58, 1)))
    a_cantos = profiles.get("away", {}).get("corners", ind.get("corners_away", round(exp_cantos * 0.42, 1)))
    h_cards = profiles.get("home", {}).get("cards", ind.get("cards_home", round(exp_cards * 0.45, 1)))
    a_cards = profiles.get("away", {}).get("cards", ind.get("cards_away", round(exp_cards * 0.55, 1)))

    st.divider()
    st.markdown("#### 📈 Projeção Comparativa por Time")
    chart_df = pd.DataFrame({
        "Métrica": ["Finalizações", "No Alvo", "Cantos", "Cartões"],
        f"{home} (Casa)": [h_shots, h_sot, h_cantos, h_cards],
        f"{away} (Fora)": [a_shots, a_sot, a_cantos, a_cards],
    }).set_index("Métrica")
    st.bar_chart(chart_df, horizontal=True, stack=False)

st.title("⚽ Preditor Quantitativo")

data_file = os.path.join("data", "predictions_today.json")
if not os.path.exists(data_file):
    st.warning("Aguardando pipeline. Execute o motor para gerar dados.")
    st.stop()

with open(data_file, "r", encoding="utf-8") as f:
    payload = json.load(f)

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
    probs = m.get("probabilities", {})
    ind = m.get("stats_individual", {})
    profiles = m.get("team_profiles", {})
    badges = m.get("ai_badges", [])
    home = m.get("home_team", "")
    away = m.get("away_team", "")
    referee = m.get("referee", "Não divulgado")
    conf = m.get("data_confidence", "Média")
    dna = resolve_league_dna(m)

    # Gols
    g = mkts.get("goals", {})
    exp_gols = g.get("expected_total", probs.get("exp_total_goals", 0))
    p_o15 = g.get("over_1_5", {}).get("prob_over", probs.get("prob_over_15", 0))
    odd_o15 = g.get("over_1_5", {}).get("fair_odd", probs.get("odd_over_15", 0))
    p_o25 = g.get("over_2_5", {}).get("prob_over", probs.get("prob_over_25", 0))
    odd_o25 = g.get("over_2_5", {}).get("fair_odd", probs.get("odd_over_25", 0))
    p_btts = g.get("btts", {}).get("prob_yes", probs.get("prob_btts", 0))
    odd_btts = g.get("btts", {}).get("fair_odd", probs.get("odd_btts", 0))

    # BTTS ou +2.5
    combo = g.get("btts_or_over25", {})
    prob_combo = combo.get("prob_hit", 0)
    fair_odd_combo = combo.get("fair_odd", 0)
    if prob_combo == 0 and (p_btts > 0 or p_o25 > 0):
        prob_combo = round(min(95.0, max(p_btts, p_o25) + 12.0), 1)
        fair_odd_combo = round(100.0 / prob_combo, 2) if prob_combo > 0 else 0

    # Cantos
    c = mkts.get("corners", {})
    exp_cantos = c.get("expected_total", ind.get("corners_total", 9.5))
    p_c85 = c.get("over_8_5", {}).get("prob_over", 0)
    odd_c85 = c.get("over_8_5", {}).get("fair_odd_over", 0)
    p_c105 = c.get("over_10_5", {}).get("prob_over", 0)
    odd_c105 = c.get("over_10_5", {}).get("fair_odd_over", 0)
    if p_c85 == 0 and exp_cantos > 0:
        p_c85 = round(min(92.0, max(45.0, (exp_cantos / 9.5) * 65.0)), 1)
        odd_c85 = round(100.0 / p_c85, 2) if p_c85 > 0 else 0
        p_c105 = round(max(20.0, p_c85 - 24.0), 1)
        odd_c105 = round(100.0 / p_c105, 2) if p_c105 > 0 else 0

    # Chutes
    s = mkts.get("shots", {})
    exp_shots = s.get("expected_shots", 0)
    sot = s.get("over_8_5_sot", {})
    p_sot = sot.get("prob_over", 0)
    odd_sot = sot.get("fair_odd", 0)
    if exp_shots == 0 and exp_gols > 0:
        exp_shots = round(exp_gols * 9.5 + 4.0, 1)
        p_sot = round(min(88.0, max(40.0, (exp_shots / 24.0) * 62.0)), 1)
        odd_sot = round(100.0 / p_sot, 2) if p_sot > 0 else 0

    # Cartões
    cd = mkts.get("cards", {})
    exp_cards = cd.get("expected_total", ind.get("cards_total", 4.5))
    ref_factor = cd.get("referee_factor", 1.0)
    p_cd35 = cd.get("over_3_5", {}).get("prob_over", 0)
    odd_cd35 = cd.get("over_3_5", {}).get("fair_odd", 0)
    p_cd45 = cd.get("over_4_5", {}).get("prob_over", 0)
    odd_cd45 = cd.get("over_4_5", {}).get("fair_odd", 0)
    if p_cd35 == 0 and exp_cards > 0:
        p_cd35 = round(min(92.0, max(45.0, (exp_cards / 4.5) * 68.0)), 1)
        odd_cd35 = round(100.0 / p_cd35, 2) if p_cd35 > 0 else 0
        p_cd45 = round(max(22.0, p_cd35 - 23.0), 1)
        odd_cd45 = round(100.0 / p_cd45, 2) if p_cd45 > 0 else 0

    # Mando individual
    h_c = profiles.get("home", {}).get("corners", ind.get("corners_home", round(exp_cantos * 0.58, 1)))
    a_c = profiles.get("away", {}).get("corners", ind.get("corners_away", round(exp_cantos * 0.42, 1)))
    h_cd = profiles.get("home", {}).get("cards", ind.get("cards_home", round(exp_cards * 0.45, 1)))
    a_cd = profiles.get("away", {}).get("cards", ind.get("cards_away", round(exp_cards * 0.55, 1)))

    with st.expander(f"{home} vs {away}", expanded=True):
        col_hdr, col_btn = st.columns([3, 1])
        with col_hdr:
            st.markdown(
                f"<span class='badge-league'>{m.get('league')}</span>"
                f"<span class='badge-dna'>{dna}</span>"
                f"<span class='badge-conf'>Amostra: {conf}</span> | Árbitro: **{referee}**",
                unsafe_allow_html=True
            )
        with col_btn:
            if st.button("📋 Resumo (Print)", key=f"btn_pop_{idx}"):
                show_match_summary_dialog(m)

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

        with tab_grafico:
            h_shots = profiles.get("home", {}).get("shots", round(exp_shots * 0.55, 1))
            a_shots = profiles.get("away", {}).get("shots", round(exp_shots * 0.45, 1))
            h_sot = profiles.get("home", {}).get("sot", round(h_shots * 0.35, 1))
            a_sot = profiles.get("away", {}).get("sot", round(a_shots * 0.35, 1))
            chart_df = pd.DataFrame({
                "Métrica": ["Finalizações", "Chutes no Alvo", "Escanteios", "Cartões"],
                f"{home} (Casa)": [h_shots, h_sot, h_c, h_cd],
                f"{away} (Fora)": [a_shots, a_sot, a_c, a_cd],
            }).set_index("Métrica")
            st.write("**Projeção Volumétrica por Equipe:**")
            st.bar_chart(chart_df, horizontal=True, stack=False)

        with tab_cantos:
            st.write(f"Média Esperada: **{exp_cantos} cantos**")
            st.caption(f"🚩 **{home} (Casa):** ~{h_c} cantos | **{away} (Fora):** ~{a_c} cantos")
            c1, c2 = st.columns(2)
            c1.metric("+8.5 Cantos", f"{p_c85}%", f"Odd: @{odd_c85}")
            c2.metric("+10.5 Cantos", f"{p_c105}%", f"Odd: @{odd_c105}")

        with tab_chutes:
            st.metric("Finalizações Totais Esperadas", exp_shots)
            st.metric("+8.5 Chutes no Alvo", f"{p_sot}%", f"Odd: @{odd_sot}")

        with tab_cards:
            st.write(f"Fator Árbitro: **{ref_factor}x** | Média Esperada: **{exp_cards}**")
            st.caption(f"🟨 **{home} (Casa):** ~{h_cd} cartões | **{away} (Fora):** ~{a_cd} cartões")
            c1, c2 = st.columns(2)
            c1.metric("+3.5 Cartões", f"{p_cd35}%", f"Odd: @{odd_cd35}")
            c2.metric("+4.5 Cartões", f"{p_cd45}%", f"Odd: @{odd_cd45}")