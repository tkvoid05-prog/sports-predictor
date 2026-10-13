import os
import json
import logging
from datetime import datetime, timezone, timedelta

from engine.fetchers import fetch_espn_fixtures
from engine.models import analyze_match_markets, InsufficientDataError

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def generate_ai_badges(goals_analysis: dict, corners_analysis: dict = None, shots_analysis: dict = None) -> list:
    """Gera badges baseadas em probabilidades reais."""
    badges = []
    p_o15 = goals_analysis["over_1_5"]["prob"]
    p_btts = goals_analysis["btts"]["prob"]
    p_combo = goals_analysis["btts_or_over25"]["prob"]

    if p_o15 >= 72.0:
        badges.append({"tipo": "green", "texto": f"Dica IA: Forte tendência +1.5 Gols ({p_o15}%) — Modelo Dixon-Coles"})
    elif p_o15 <= 58.0:
        badges.append({"tipo": "orange", "texto": f"Atenção IA: Jogo Amarrado / Tendência Under ({p_o15}% para +1.5)"})

    if p_btts >= 55.0:
        badges.append({"tipo": "green", "texto": f"Dica IA: Alta probabilidade de BTTS / Ambas Marcam ({p_btts}%)"})

    if p_combo >= 75.0:
        badges.append({"tipo": "green", "texto": f"Dica IA: Combo BTTS ou Over 2.5 com forte aderência estatística ({p_combo}%)"})

    # Badges para mercados secundários (se existirem)
    if corners_analysis and corners_analysis.get("expected_total") is not None:
        exp_c = corners_analysis["expected_total"]
        if exp_c >= 10.5:
            badges.append({"tipo": "green", "texto": f"Dica IA: Volume Alto de Cantos (Média {exp_c})"})
            
    if shots_analysis and shots_analysis.get("expected_sot") is not None:
        exp_sot = shots_analysis["expected_sot"]
        if exp_sot >= 9.5:
            badges.append({"tipo": "green", "texto": f"Dica IA: Alta precisão ofensiva (Média {exp_sot} no alvo)"})

    return badges


def run_pipeline():
    fixtures = fetch_espn_fixtures()
    matches_payload = []
    skipped_count = 0

    for f in fixtures:
        league = f.get("league", "Outros")
        home = f.get("home_team", "")
        away = f.get("away_team", "")
        referee = f.get("referee", "Não divulgado")
        kickoff = f.get("kickoff", "")

        # NOVO: Ler as chaves atualizadas pelo fetchers.py da Fase 2
        h_stats = f.get("home_stats")
        a_stats = f.get("away_stats")

        if not h_stats or not a_stats:
            logger.warning(f"Partida descartada (dados ausentes): {home} vs {away}")
            skipped_count += 1
            continue

        try:
            # O models.py agora recebe as listas completas de stats
            result = analyze_match_markets(h_stats, a_stats)
        except InsufficientDataError as e:
            logger.warning(f"Partida descartada pelo modelo: {home} vs {away} | {e}")
            skipped_count += 1
            continue
        except Exception as e:
            logger.error(f"Erro inesperado no modelo para {home} vs {away}: {e}")
            skipped_count += 1
            continue

        goals = result["goals"]
        corners = result.get("corners", {})
        shots = result.get("shots", {})
        cards = result.get("cards", {})
        model_info = result.get("model_info", {})

        h_sample = model_info.get("home_sample_size", 0)
        a_sample = model_info.get("away_sample_size", 0)
        confidence = "Alta" if (h_sample >= 5 and a_sample >= 5) else "Média"

        badges = generate_ai_badges(goals, corners, shots)

        match_obj = {
            "league": league,
            "league_dna": league,
            "home_team": home,
            "away_team": away,
            "referee": referee,
            "kickoff": kickoff,
            "data_confidence": confidence,
            "ai_badges": badges,
            "probabilities": {
                "exp_total_goals": goals["expected_total"],
                "prob_over_15": goals["over_1_5"]["prob"],
                "odd_over_15": goals["over_1_5"]["fair_odd"],
                "prob_over_25": goals["over_2_5"]["prob"],
                "odd_over_25": goals["over_2_5"]["fair_odd"],
                "prob_btts": goals["btts"]["prob"],
                "odd_btts": goals["btts"]["fair_odd"],
            },
            "markets": {
                "goals": {
                    "expected_total": goals["expected_total"],
                    "lambda_h": goals["lambda_h"],
                    "mu_a": goals["mu_a"],
                    "over_1_5": {"prob_over": goals["over_1_5"]["prob"], "fair_odd": goals["over_1_5"]["fair_odd"]},
                    "over_2_5": {"prob_over": goals["over_2_5"]["prob"], "fair_odd": goals["over_2_5"]["fair_odd"]},
                    "btts": {"prob_yes": goals["btts"]["prob"], "fair_odd": goals["btts"]["fair_odd"]},
                    "btts_or_over25": {"prob_hit": goals["btts_or_over25"]["prob"], "fair_odd": goals["btts_or_over25"]["fair_odd"]},
                    # Novos mercados de gols por time (se o models.py retornar)
                    "home_over_1_5": goals.get("home_over_1_5"),
                    "away_over_1_5": goals.get("away_over_1_5"),
                    "home_win_prob": goals.get("home_win_prob"),
                    "draw_prob": goals.get("draw_prob"),
                    "away_win_prob": goals.get("away_win_prob"),
                },
                "corners": corners if corners.get("expected_total") is not None else {"status": "awaiting_real_data", "expected_total": None},
                "shots": shots if shots.get("expected_total") is not None else {"status": "awaiting_real_data", "expected_shots": None},
                "cards": cards if cards.get("expected_total") is not None else {"status": "awaiting_real_data", "expected_total": None},
            },
            "team_profiles": {
                "home": {"shots": h_stats.get("shots"), "sot": h_stats.get("shots_on_target"), "corners": h_stats.get("corners"), "cards": h_stats.get("cards")},
                "away": {"shots": a_stats.get("shots"), "sot": a_stats.get("shots_on_target"), "corners": a_stats.get("corners"), "cards": a_stats.get("cards")},
            },
            "stats_individual": {
                "corners_home": h_stats.get("corners"),
                "corners_away": a_stats.get("corners"),
                "cards_home": h_stats.get("cards"),
                "cards_away": a_stats.get("cards"),
            },
            "model_info": model_info,
        }

        matches_payload.append(match_obj)

    logger.info(f"Pipeline concluído. Partidas analisadas: {len(matches_payload)} | Descartadas: {skipped_count}")

    br_tz = timezone(timedelta(hours=-3))
    now = datetime.now(br_tz)
    shift = "RODADA DA MANHÃ" if now.hour < 13 else "RODADA DA TARDE/NOITE"

    output_data = {
        "shift": shift,
        "updated_at": now.isoformat(),
        "matches": matches_payload,
    }

    os.makedirs("data", exist_ok=True)
    with open(os.path.join("data", "predictions_today.json"), "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    run_pipeline()