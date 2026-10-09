import json
import os
import sys
from datetime import datetime

# Garante que as importações encontram a pasta raiz sem erros
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from engine.fetchers import fetch_european_league_data, fetch_espn_fixtures
from engine.models import analyze_match_markets


def get_current_shift() -> str:
    """
    Determina o turno atual:
    - Antes das 13h: Turno da Manhã (jogos até às 13:59)
    - A partir das 13h: Turno da Tarde/Noite (jogos a partir das 14:00)
    """
    now = datetime.now()
    return "manha" if now.hour < 13 else "tarde_noite"


def run_pipeline():
    shift = get_current_shift()
    print(f"[*] A iniciar processamento - Turno: {shift.upper()}")

    os.makedirs("data", exist_ok=True)

    # 1. Carrega dados de ligas europeias (football-data.co.uk)
    leagues = ["Premier League", "La Liga", "Bundesliga", "Ligue 1"]
    league_dfs = {}
    for lg in leagues:
        df = fetch_european_league_data(lg)
        if not df.empty:
            league_dfs[lg] = df

    # 2. Carrega partidas do Brasileirão via ESPN
    brazil_fixtures = fetch_espn_fixtures()

    predictions = []

    # Se a ESPN devolver jogos, processa as previsões
    for fix in brazil_fixtures:
        h_stats = {"avg_goals_for": 1.4, "avg_goals_against": 1.1, "avg_corners_for": 5.4, "avg_shots": 13.0, "avg_shots_target": 4.5, "avg_fouls": 15.0, "avg_cards": 2.6}
        a_stats = {"avg_goals_for": 1.0, "avg_goals_against": 1.3, "avg_corners_for": 4.5, "avg_shots": 11.0, "avg_shots_target": 3.8, "avg_fouls": 14.5, "avg_cards": 2.8}

        ref_info = {"league_avg_cards": 5.2, "referee_avg_cards": 5.6}
        markets = analyze_match_markets(h_stats, a_stats, ref_info)

        predictions.append({
            "league": fix["league"],
            "home_team": fix["home_team"],
            "away_team": fix["away_team"],
            "kickoff": fix.get("kickoff", ""),
            "referee": fix.get("referee", "Não divulgado"),
            "markets": markets
        })

    # Grava o ficheiro estático de saída em formato JSON
    output_path = os.path.join("data", "predictions_today.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"updated_at": datetime.now().isoformat(), "shift": shift, "matches": predictions}, f, indent=2, ensure_ascii=False)

    print(f"[+] Concluído! Ficheiro gerado com sucesso em: {output_path}")


if __name__ == "__main__":
    run_pipeline()