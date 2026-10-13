import json
from datetime import datetime

with open("data/predictions_today.json", "r", encoding="utf-8") as f:
    data = json.load(f)

matches = data.get("matches", [])
print(f"Total de partidas: {len(matches)}")
print(f"Turno: {data.get('shift', 'N/A')}")
print(f"Atualizado em: {data.get('updated_at', 'N/A')[:19]}")
print("-" * 80)

for i, m in enumerate(matches, 1):
    league = m.get("league", "N/A")
    home = m.get("home_team", "?")
    away = m.get("away_team", "?")
    kickoff = m.get("kickoff", "N/A")
    conf = m.get("data_confidence", "N/A")
    exp = m["markets"]["goals"]["expected_total"]
    p_o15 = m["markets"]["goals"]["over_1_5"]["prob_over"]
    p_btts = m["markets"]["goals"]["btts"]["prob_yes"]
    
    # Converte kickoff UTC para BRT (opcional)
    try:
        kt = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
        kt_brt = kt.astimezone(datetime.now().astimezone().tzinfo)  # apenas exibição
        kickoff_fmt = kt_brt.strftime("%d/%m %H:%M")
    except Exception:
        kickoff_fmt = kickoff
    
    print(f"{i:2}. [{league:20}] {home} vs {away}")
    print(f"    Horário: {kickoff_fmt} | Confiança: {conf}")
    print(f"    Gols esperados: {exp} | Over 1.5: {p_o15}% | BTTS: {p_btts}%")
    print()