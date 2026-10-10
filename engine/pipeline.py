from datetime import datetime
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from engine.fetchers import fetch_espn_fixtures
from engine.models import analyze_match_markets


def get_current_shift() -> str:
  now = datetime.now()
  return "manha" if now.hour < 13 else "tarde_noite"


def build_stats_from_last_5(history: dict) -> dict:
  """Calcula a força de ataque e vulnerabilidade de defesa com base nos 5 jogos reais."""
  scored = history.get("goals_scored", [1.2])
  conceded = history.get("goals_conceded", [1.1])

  # Média ponderada dando maior peso aos jogos mais recentes da lista
  weights = np.array([0.1, 0.15, 0.2, 0.25, 0.3])[-len(scored) :]
  weights = weights / np.sum(weights)

  avg_scored = float(np.sum(np.array(scored) * weights))
  avg_conceded = float(np.sum(np.array(conceded) * weights))

  league_baseline = 1.35
  return {
      "attack_strength": max(0.4, avg_scored / league_baseline),
      "defense_vulnerability": max(0.4, avg_conceded / league_baseline),
      "avg_corners_for": 5.1,
      "avg_shots": 12.5,
      "avg_shots_target": 4.2,
      "avg_fouls": 13.0,
      "avg_cards": 2.1,
  }


def run_pipeline():
  shift = get_current_shift()
  print(f"[*] Executando coleta de dados reais - Turno: {shift.upper()}")
  os.makedirs("data", exist_ok=True)

  fixtures = fetch_espn_fixtures()
  print(f"[*] Jogos reais encontrados no dia: {len(fixtures)}")

  predictions = []
  for fix in fixtures:
    h_stats = build_stats_from_last_5(fix["home_history_5"])
    a_stats = build_stats_from_last_5(fix["away_history_5"])
    ref_info = {"league_avg_cards": 4.8, "referee_avg_cards": 5.0}

    mkts = analyze_match_markets(h_stats, a_stats, ref_info)
    predictions.append({
        "league": fix["league"],
        "home_team": fix["home_team"],
        "away_team": fix["away_team"],
        "kickoff": fix.get("kickoff", ""),
        "referee": fix.get("referee", "Não divulgado"),
        "markets": mkts,
        "sample_info": {
            "home_sample": fix["home_history_5"].get("sample_size", 0),
            "away_sample": fix["away_history_5"].get("sample_size", 0),
        },
    })

  output_path = os.path.join("data", "predictions_today.json")
  with open(output_path, "w", encoding="utf-8") as f:
    json.dump(
        {
            "updated_at": datetime.now().isoformat(),
            "shift": shift,
            "matches": predictions,
        },
        f,
        indent=2,
        ensure_ascii=False,
    )

  print(f"[+] Pipeline finalizado com dados reais: {output_path}")


if __name__ == "__main__":
  run_pipeline()