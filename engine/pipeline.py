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

def build_stats_from_last_5(history: dict) -> dict:
    scored = history.get("goals_scored", [])
    conceded = history.get("goals_conceded", [])
    sample_size = history.get("sample_size", 0)
    
    league_baseline = 1.35
    
    # Se tiver menos de 3 jogos reais registrados, aplica suavização pesada para a média da liga
    if sample_size < 3:
        return {
            "attack_strength": 1.0,
            "defense_vulnerability": 1.0,
            "avg_corners_for": 5.0,
            "avg_shots": 12.0,
            "avg_shots_target": 4.0,
            "avg_cards": 2.1,
            "confidence": "Baixa (Amostra Reduzida)"
        }
        
    weights = np.array([0.10, 0.15, 0.20, 0.25, 0.30])[-len(scored):]
    weights = weights / np.sum(weights)
    
    avg_scored = float(np.sum(np.array(scored) * weights))
    avg_conceded = float(np.sum(np.array(conceded) * weights))
    
    # Encolhimento Bayesiano: pondera amostra com prior da liga (peso = sample / (sample + 2))
    shrinkage = sample_size / (sample_size + 2.0)
    att_strength = (avg_scored / league_baseline) * shrinkage + (1.0 * (1.0 - shrinkage))
    def_vulner = (avg_conceded / league_baseline) * shrinkage + (1.0 * (1.0 - shrinkage))
    
    conf = "Alta" if sample_size >= 5 else "Média"
    
    return {
        "attack_strength": float(att_strength),
        "defense_vulnerability": float(def_vulner),
        "avg_corners_for": 5.1,
        "avg_shots": 12.5,
        "avg_shots_target": 4.2,
        "avg_cards": 2.1,
        "confidence": conf
    }

def run_pipeline():
    shift = get_current_shift()
    print(f"[*] Executando calibração quantitativa - Turno: {shift.upper()}")
    os.makedirs("data", exist_ok=True)

    fixtures = fetch_espn_fixtures()
    print(f"[*] Jogos identificados: {len(fixtures)}")

    predictions = []
    for fix in fixtures:
        h_stats = build_stats_from_last_5(fix["home_history_5"])
        a_stats = build_stats_from_last_5(fix["away_history_5"])
        ref_info = {"league_avg_cards": 4.8, "referee_avg_cards": 5.0}

        mkts = analyze_match_markets(h_stats, a_stats, ref_info)
        
        # Confiança geral do confronto
        data_conf = "Alta" if (h_stats["confidence"] == "Alta" and a_stats["confidence"] == "Alta") else "Média"
        if "Baixa" in (h_stats["confidence"], a_stats["confidence"]):
            data_conf = "Amostra Limitada"

        predictions.append({
            "league": fix["league"],
            "home_team": fix["home_team"],
            "away_team": fix["away_team"],
            "kickoff": fix.get("kickoff", ""),
            "referee": fix.get("referee", "Não divulgado"),
            "data_confidence": data_conf,
            "markets": mkts
        })

    output_path = os.path.join("data", "predictions_today.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"updated_at": datetime.now().isoformat(), "shift": shift, "matches": predictions}, f, indent=2, ensure_ascii=False)

    print(f"[+] Base calibrada com sucesso: {output_path}")

if __name__ == "__main__":
    run_pipeline()