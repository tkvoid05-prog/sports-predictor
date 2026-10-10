import os
import sys
import json
from datetime import datetime
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.fetchers import fetch_espn_fixtures
from engine.models import analyze_match_markets

def get_current_shift() -> str:
    now = datetime.now()
    return "manha" if now.hour < 13 else "tarde_noite"

def build_team_profile(history: dict, is_home: bool) -> dict:
    scored = history.get("goals_scored", [])
    conceded = history.get("goals_conceded", [])
    sample_size = history.get("sample_size", 0)
    
    baseline_goals = 1.35
    if sample_size < 3:
        return {
            "attack_strength": 1.0,
            "defense_vulnerability": 1.0,
            "exp_shots": 13.0 if is_home else 10.5,
            "exp_sot": 4.5 if is_home else 3.5,
            "exp_corners": 5.5 if is_home else 4.0,
            "confidence": "Amostra Reduzida"
        }
        
    weights = np.array([0.10, 0.15, 0.20, 0.25, 0.30])[-len(scored):]
    weights = weights / np.sum(weights)
    
    avg_scored = float(np.sum(np.array(scored) * weights))
    avg_conceded = float(np.sum(np.array(conceded) * weights))
    
    # Encolhimento Bayesiano
    shrinkage = sample_size / (sample_size + 2.0)
    att = float(np.clip((avg_scored / baseline_goals) * shrinkage + (1.0 - shrinkage), 0.5, 2.5))
    defn = float(np.clip((avg_conceded / baseline_goals) * shrinkage + (1.0 - shrinkage), 0.5, 2.5))
    
    # Volume com fator de mando (Arsenal em casa chuta mais)
    bias = 1.15 if is_home else 0.88
    shots = round(att * 11.5 * bias, 1)
    sot = round(att * 3.8 * bias, 1)
    corners = round(att * 4.6 * bias, 1)
    
    conf = "Alta" if sample_size >= 5 else "Média"
    return {
        "attack_strength": att,
        "defense_vulnerability": defn,
        "exp_shots": shots,
        "exp_sot": sot,
        "exp_corners": corners,
        "confidence": conf
    }

def run_pipeline():
    shift = get_current_shift()
    print(f"[*] Executando pipeline com perfis volumétricos - Turno: {shift.upper()}")
    os.makedirs("data", exist_ok=True)

    fixtures = fetch_espn_fixtures()
    predictions = []

    for fix in fixtures:
        h_profile = build_team_profile(fix["home_history_5"], is_home=True)
        a_profile = build_team_profile(fix["away_history_5"], is_home=False)
        ref_info = {"league_avg_cards": 4.8, "referee_avg_cards": 5.0}

        mkts = analyze_match_markets(h_profile, a_profile, ref_info)

        predictions.append({
            "league": fix["league"],
            "home_team": fix["home_team"],
            "away_team": fix["away_team"],
            "kickoff": fix.get("kickoff", ""),
            "referee": fix.get("referee", "Não divulgado"),
            "data_confidence": "Alta" if (h_profile["confidence"] == "Alta" and a_profile["confidence"] == "Alta") else "Média",
            "team_profiles": {
                "home": {
                    "shots": h_profile["exp_shots"],
                    "sot": h_profile["exp_sot"],
                    "corners": h_profile["exp_corners"]
                },
                "away": {
                    "shots": a_profile["exp_shots"],
                    "sot": a_profile["exp_sot"],
                    "corners": a_profile["exp_corners"]
                }
            },
            "markets": mkts
        })

    output_path = os.path.join("data", "predictions_today.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"updated_at": datetime.now().isoformat(), "shift": shift, "matches": predictions}, f, indent=2, ensure_ascii=False)

    print(f"[+] Concluído com métricas volumétricas: {output_path}")

if __name__ == "__main__":
    run_pipeline()