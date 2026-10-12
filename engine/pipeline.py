import os
import json
import logging
from datetime import datetime, timezone, timedelta

from engine.fetchers import fetch_espn_fixtures
from engine.models import analyze_match_markets, InsufficientDataError

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def generate_ai_badges(goals_analysis: dict) -> list:
    """Gera badges baseadas exclusivamente em probabilidades reais de gols (Dixon-Coles)."""
    badges = []
    p_o15 = goals_analysis["over_1_5"]["prob"]
    p_btts = goals_analysis["btts"]["prob"]
    p_combo = goals_analysis["btts_or_over25"]["prob"]

    if p_o15 >= 72.0:
        badges.append({
            "tipo": "green",
            "texto": f"Dica IA: Forte tendência +1.5 Gols ({p_o15}%) — Modelo Dixon-Coles"
        })
    elif p_o15 <= 58.0:
        badges.append({
            "tipo": "orange",
            "texto": f"Atenção IA: Jogo Amarrado / Tendência Under ({p_o15}% para +1.5)"
        })

    if p_btts >= 55.0:
        badges.append({
            "tipo": "green",
            "texto": f"Dica IA: Alta probabilidade de BTTS / Ambas Marcam ({p_btts}%)"
        })

    if p_combo >= 75.0:
        badges.append({
            "tipo": "green",
            "texto": f"Dica IA: Combo BTTS ou Over 2.5 com forte aderência estatística ({p_combo}%)"
        })

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

        h_hist = f.get("home_history_5")
        a_hist = f.get("away_history_5")

        # Regra de integridade: sem histórico real, a partida não é analisável
        if not h_hist or not a_hist:
            logger.warning(f"Partida descartada (histórico ausente): {home} vs {away}")
            skipped_count += 1
            continue

        try:
            result = analyze_match_markets(h_hist, a_hist)
        except InsufficientDataError as e:
            logger.warning(f"Partida descartada pelo modelo: {home} vs {away} | {e}")
            skipped_count += 1
            continue
        except Exception as e:
            logger.error(f"Erro inesperado no modelo para {home} vs {away}: {e}")
            skipped_count += 1
            continue

        goals = result["goals"]
        model_info = result["model_info"]

        h_sample = model_info["home_sample_size"]
        a_sample = model_info["away_sample_size"]
        confidence = "Alta" if (h_sample >= 5 and a_sample >= 5) else "Média"

        badges = generate_ai_badges(goals)

        # Schema de saída preservado para compatibilidade com o app.py.
        # Mercados secundários retornam None explícito até a Fase 2 (dados reais via endpoint summary/boxscore).
        match_obj = {
            "league": league,
            "league_dna": league,  # mantido como identificador neutro (dado real: nome da liga)
            "home_team": home,
            "away_team": away,
            "referee": referee,
            "kickoff": kickoff,
            "data_confidence": confidence,
            "ai_badges": badges,

            # Compatibilidade com o formato legado consumido pelo app.py
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
                },
                # Fase 1: mercados secundários desativados por ausência de dados reais na API /schedule
                "corners": {
                    "status": "awaiting_real_data",
                    "expected_total": None,
                    "over_8_5": {"prob_over": None, "fair_odd_over": None},
                    "over_10_5": {"prob_over": None, "fair_odd_over": None},
                },
                "shots": {
                    "status": "awaiting_real_data",
                    "expected_shots": None,
                    "over_8_5_sot": {"prob_over": None, "fair_odd": None},
                },
                "cards": {
                    "status": "awaiting_real_data",
                    "referee_factor": None,
                    "expected_total": None,
                    "over_3_5": {"prob_over": None, "fair_odd": None},
                    "over_4_5": {"prob_over": None, "fair_odd": None},
                },
            },

            # Estruturas preservadas com None para não quebrar o app.py até a Fase 4
            "team_profiles": {
                "home": {"shots": None, "sot": None, "corners": None, "cards": None},
                "away": {"shots": None, "sot": None, "corners": None, "cards": None},
            },
            "stats_individual": {
                "corners_home": None,
                "corners_away": None,
                "corners_total": None,
                "cards_home": None,
                "cards_away": None,
                "cards_total": None,
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