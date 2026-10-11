import os
import json
import math
from datetime import datetime, timezone, timedelta
from engine.fetchers import fetch_espn_fixtures, fetch_team_recent_stats

# Benchmark e DNA específico por competição
LEAGUE_PROFILES = {
    "Premier League": {
        "tag": "⚡ Ritmo Alto | 🚩 +Cantos | 🟨 -Cartões",
        "pace_mult": 1.10,
        "corner_mult": 1.08,
        "card_mult": 0.85,
        "desc_cantos": "Ritmo vertical e transição rápida da Premier League.",
        "desc_cards": "Árbitros ingleses mais permissivos em faltas táticas."
    },
    "Brasileirão Série A": {
        "tag": "🛑 Jogo Picardado | 🟨 +Cartões | ⏱️ Ritmo Médio",
        "pace_mult": 0.95,
        "corner_mult": 0.97,
        "card_mult": 1.25,
        "desc_cantos": "Padrão de volume lateral da Série A.",
        "desc_cards": "Rigor disciplinar alto característico do futebol brasileiro."
    },
    "La Liga": {
        "tag": "🎯 Posse Cadenciada | 🟨 +Cartões",
        "pace_mult": 0.98,
        "corner_mult": 0.96,
        "card_mult": 1.20,
        "desc_cantos": "Circulação paciente reduz cantos de transição.",
        "desc_cards": "Critério disciplinar rígido da La Liga."
    },
    "DEFAULT": {
        "tag": "⚖️ Padrão Equilibrado",
        "pace_mult": 1.0,
        "corner_mult": 1.0,
        "card_mult": 1.0,
        "desc_cantos": "Projeção volumétrica equilibrada.",
        "desc_cards": "Critério disciplinar padrão."
    }
}

def get_league_profile(league_name):
    for key, data in LEAGUE_PROFILES.items():
        if key.lower() in league_name.lower():
            return data
    return LEAGUE_PROFILES["DEFAULT"]

def poisson_prob(lmbda, k):
    if lmbda <= 0:
        return 1.0 if k == 0 else 0.0
    return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)

def calc_poisson_goals(exp_home, exp_away):
    p_home = [poisson_prob(exp_home, k) for k in range(10)]
    p_away = [poisson_prob(exp_away, k) for k in range(10)]

    p_over_15 = 0.0
    p_over_25 = 0.0
    p_btts = 0.0

    for i in range(10):
        for j in range(10):
            prob = p_home[i] * p_away[j]
            total_goals = i + j
            if total_goals > 1.5:
                p_over_15 += prob
            if total_goals > 2.5:
                p_over_25 += prob
            if i > 0 and j > 0:
                p_btts += prob

    prob_o15 = round(p_over_15 * 100, 1)
    prob_o25 = round(p_over_25 * 100, 1)
    prob_btts = round(p_btts * 100, 1)

    odd_o15 = round(100.0 / prob_o15, 2) if prob_o15 > 0 else 0
    odd_o25 = round(100.0 / prob_o25, 2) if prob_o25 > 0 else 0
    odd_btts = round(100.0 / prob_btts, 2) if prob_btts > 0 else 0

    return prob_o15, odd_o15, prob_o25, odd_o25, prob_btts, odd_btts

def generate_ai_badges(prob_o15, prob_btts, expected_corners, expected_cards, league_profile):
    badges = []

    # Gols
    if prob_o15 >= 70.0:
        badges.append({
            "tipo": "green",
            "texto": f"Dica IA: Forte tendência +1.5 Gols ({prob_o15}%)"
        })
    elif prob_o15 >= 60.0:
        badges.append({
            "tipo": "orange",
            "texto": f"Atenção IA: Tendência Moderada de Gols ({prob_o15}%)"
        })

    # Escanteios (Calibrado pelo DNA da Liga)
    if expected_corners >= 10.0:
        badges.append({
            "tipo": "green",
            "texto": f"Dica IA: Volume Alto de Cantos (+8.5 / +9.5) — {league_profile['desc_cantos']}"
        })
    elif expected_corners >= 9.0:
        badges.append({
            "tipo": "orange",
            "texto": "Atenção IA: Volume Médio de Cantos (+8.5 justo)"
        })

    # Cartões (Calibrado pelo DNA da Liga e Árbitro)
    if expected_cards >= 4.5:
        badges.append({
            "tipo": "green",
            "texto": f"Dica IA: Tendência Disciplinar Alta (+3.5 / +4.5 Cartões) — {league_profile['desc_cards']}"
        })
    elif expected_cards <= 3.2:
        badges.append({
            "tipo": "orange",
            "texto": f"Atenção IA: Jogo Limpo / Poucos Cartões (Abaixo de 3.5) — {league_profile['desc_cards']}"
        })

    return badges

def run_pipeline():
    fixtures = fetch_espn_fixtures()
    matches_payload = []

    for f in fixtures:
        league = f.get("league", "Outros")
        home = f.get("home_team", "")
        away = f.get("away_team", "")
        referee = f.get("referee", "Não divulgado")
        ref_factor = f.get("referee_factor", 1.0)

        home_stats = fetch_team_recent_stats(home, is_home=True)
        away_stats = fetch_team_recent_stats(away, is_home=False)

        profile = get_league_profile(league)

        # 1. Projeção de Gols
        exp_home_goals = home_stats.get("avg_scored", 1.3)
        exp_away_goals = away_stats.get("avg_scored", 1.1)
        exp_total_goals = round(exp_home_goals + exp_away_goals, 1)

        p_o15, odd_o15, p_o25, odd_o25, p_btts, odd_btts = calc_poisson_goals(exp_home_goals, exp_away_goals)
        p_combo = round(min(95.0, max(p_btts, p_o25) + 12.0), 1)
        odd_combo = round(100.0 / p_combo, 2) if p_combo > 0 else 0

        # 2. Escanteios (com benchmark)
        raw_home_corners = home_stats.get("avg_corners", 5.5)
        raw_away_corners = away_stats.get("avg_corners", 4.3)
        h_corners = round(raw_home_corners * profile["corner_mult"], 1)
        a_corners = round(raw_away_corners * profile["corner_mult"], 1)
        exp_corners = round(h_corners + a_corners, 1)

        p_c85 = round(min(92.0, max(45.0, (exp_corners / 9.5) * 65.0)), 1)
        odd_c85 = round(100.0 / p_c85, 2) if p_c85 > 0 else 0
        p_c105 = round(max(20.0, p_c85 - 24.0), 1)
        odd_c105 = round(100.0 / p_c105, 2) if p_c105 > 0 else 0

        # 3. Finalizações (com benchmark)
        raw_home_shots = home_stats.get("avg_shots", 14.0)
        raw_away_shots = away_stats.get("avg_shots", 11.0)
        h_shots = round(raw_home_shots * profile["pace_mult"], 1)
        a_shots = round(raw_away_shots * profile["pace_mult"], 1)
        exp_shots = round(h_shots + a_shots, 1)

        h_sot = round(home_stats.get("avg_sot", h_shots * 0.35), 1)
        a_sot = round(away_stats.get("avg_sot", a_shots * 0.35), 1)
        p_sot = round(min(88.0, max(40.0, (exp_shots / 24.0) * 62.0)), 1)
        odd_sot = round(100.0 / p_sot, 2) if p_sot > 0 else 0

        # 4. Cartões (com benchmark e árbitro)
        raw_home_cards = home_stats.get("avg_cards", 2.2)
        raw_away_cards = away_stats.get("avg_cards", 2.4)
        h_cards = round(raw_home_cards * profile["card_mult"] * ref_factor, 1)
        a_cards = round(raw_away_cards * profile["card_mult"] * ref_factor, 1)
        exp_cards = round(h_cards + a_cards, 1)

        p_cd35 = round(min(92.0, max(45.0, (exp_cards / 4.5) * 68.0)), 1)
        odd_cd35 = round(100.0 / p_cd35, 2) if p_cd35 > 0 else 0
        p_cd45 = round(max(22.0, p_cd35 - 23.0), 1)
        odd_cd45 = round(100.0 / p_cd45, 2) if p_cd45 > 0 else 0

        badges = generate_ai_badges(p_o15, p_btts, exp_corners, exp_cards, profile)

        match_obj = {
            "league": league,
            "league_dna": profile["tag"],
            "home_team": home,
            "away_team": away,
            "referee": referee,
            "data_confidence": "Média",
            "ai_badges": badges,
            "team_profiles": {
                "home": {"shots": h_shots, "sot": h_sot, "corners": h_corners, "cards": h_cards},
                "away": {"shots": a_shots, "sot": a_sot, "corners": a_corners, "cards": a_cards}
            },
            "stats_individual": {
                "corners_home": h_corners,
                "corners_away": a_corners,
                "corners_total": exp_corners,
                "cards_home": h_cards,
                "cards_away": a_cards,
                "cards_total": exp_cards
            },
            "probabilities": {
                "exp_total_goals": exp_total_goals,
                "prob_over_15": p_o15,
                "odd_over_15": odd_o15,
                "prob_over_25": p_o25,
                "odd_over_25": odd_o25,
                "prob_btts": p_btts,
                "odd_btts": odd_btts
            },
            "markets": {
                "goals": {
                    "expected_total": exp_total_goals,
                    "over_1_5": {"prob_over": p_o15, "fair_odd": odd_o15},
                    "over_2_5": {"prob_over": p_o25, "fair_odd": odd_o25},
                    "btts": {"prob_yes": p_btts, "fair_odd": odd_btts},
                    "btts_or_over25": {"prob_hit": p_combo, "fair_odd": odd_combo}
                },
                "corners": {
                    "expected_total": exp_corners,
                    "over_8_5": {"prob_over": p_c85, "fair_odd_over": odd_c85},
                    "over_10_5": {"prob_over": p_c105, "fair_odd": odd_c105}
                },
                "shots": {
                    "expected_shots": exp_shots,
                    "over_8_5_sot": {"prob_over": p_sot, "fair_odd": odd_sot}
                },
                "cards": {
                    "referee_factor": ref_factor,
                    "expected_total": exp_cards,
                    "over_3_5": {"prob_over": p_cd35, "fair_odd": odd_cd35},
                    "over_4_5": {"prob_over": p_cd45, "fair_odd": odd_cd45}
                }
            }
        }
        matches_payload.append(match_obj)

    # Identificação do turno no horário de Brasília (UTC-3)
    br_tz = timezone(timedelta(hours=-3))
    now = datetime.now(br_tz)
    shift = "RODADA DA MANHÃ" if now.hour < 13 else "RODADA DA TARDE/NOITE"

    output_data = {
        "shift": shift,
        "updated_at": now.isoformat(),
        "matches": matches_payload
    }

    os.makedirs("data", exist_ok=True)
    with open(os.path.join("data", "predictions_today.json"), "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_pipeline()