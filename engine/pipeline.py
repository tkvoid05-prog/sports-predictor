import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from engine.fetchers import fetch_european_league_data, fetch_espn_fixtures
from engine.models import analyze_match_markets


def get_current_shift() -> str:
    now = datetime.now()
    return "manha" if now.hour < 13 else "tarde_noite"


def build_team_stats_decay(df: pd.DataFrame, team: str, half_life_days: float = 45.0) -> dict:
    """Calcula médias com decaimento exponencial temporal (fase recente tem maior peso)."""
    if df.empty or "HomeTeam" not in df.columns:
        return {"attack_strength": 1.0, "defense_vulnerability": 1.0, "avg_corners_for": 5.0, "avg_shots": 12.0, "avg_shots_target": 4.0, "avg_fouls": 13.0, "avg_cards": 2.2}

    team_matches = df[(df["HomeTeam"] == team) | (df["AwayTeam"] == team)].copy()
    if team_matches.empty:
        return {"attack_strength": 1.0, "defense_vulnerability": 1.0, "avg_corners_for": 5.0, "avg_shots": 12.0, "avg_shots_target": 4.0, "avg_fouls": 13.0, "avg_cards": 2.2}

    team_matches["ParsedDate"] = pd.to_datetime(team_matches["Date"], format="%d/%m/%Y", errors="coerce")
    ref_date = team_matches["ParsedDate"].max() if not team_matches["ParsedDate"].isna().all() else datetime.now()
    days_diff = (ref_date - team_matches["ParsedDate"]).dt.days.fillna(30).values
    weights = np.exp(-days_diff / half_life_days)
    sum_w = np.sum(weights) if np.sum(weights) > 0 else 1.0

    def get_metric(col_home, col_away):
        vals = np.where(team_matches["HomeTeam"] == team, team_matches[col_home].fillna(0), team_matches[col_away].fillna(0))
        return float(np.sum(vals * weights) / sum_w)

    scored = get_metric("FTHG", "FTAG")
    conceded = get_metric("FTAG", "FTHG")
    corners = get_metric("HC", "AC") if "HC" in team_matches.columns else 5.0
    shots = get_metric("HS", "AS") if "HS" in team_matches.columns else 12.0
    sot = get_metric("HST", "AST") if "HST" in team_matches.columns else 4.0
    fouls = get_metric("HF", "AF") if "HF" in team_matches.columns else 13.0
    cards = get_metric("HY", "AY") if "HY" in team_matches.columns else 2.0

    league_avg_goals = 1.35
    return {
        "attack_strength": max(0.5, scored / league_avg_goals),
        "defense_vulnerability": max(0.5, conceded / league_avg_goals),
        "avg_corners_for": corners,
        "avg_shots": shots,
        "avg_shots_target": sot,
        "avg_fouls": fouls,
        "avg_cards": cards,
    }


def run_pipeline():
    shift = get_current_shift()
    print(f"[*] Executando motor quantitativo - Turno: {shift.upper()}")
    os.makedirs("data", exist_ok=True)

    leagues = ["Premier League", "La Liga", "Bundesliga", "Ligue 1"]
    league_dfs = {lg: fetch_european_league_data(lg) for lg in leagues}

    fixtures = fetch_espn_fixtures()
    predictions = []

    for fix in fixtures:
        df_league = league_dfs.get(fix["league"], pd.DataFrame())
        h_stats = build_team_stats_decay(df_league, fix["home_team"])
        a_stats = build_team_stats_decay(df_league, fix["away_team"])
        ref_info = {"league_avg_cards": 4.8, "referee_avg_cards": 5.1}

        mkts = analyze_match_markets(h_stats, a_stats, ref_info)
        predictions.append({
            "league": fix["league"],
            "home_team": fix["home_team"],
            "away_team": fix["away_team"],
            "kickoff": fix.get("kickoff", ""),
            "referee": fix.get("referee", "Não divulgado"),
            "markets": mkts,
        })

    output_path = os.path.join("data", "predictions_today.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"updated_at": datetime.now().isoformat(), "shift": shift, "matches": predictions}, f, indent=2, ensure_ascii=False)

    print(f"[+] Concluído com sucesso em: {output_path}")


if __name__ == "__main__":
    run_pipeline()