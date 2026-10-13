import json
import requests
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    tz_brt = ZoneInfo("America/Sao_Paulo")
except ImportError:
    tz_brt = timezone(timedelta(hours=-3))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

ESPN_LEAGUES = {
    "Premier League": "eng.1",
    "La Liga": "esp.1",
    "Bundesliga": "ger.1",
    "Ligue 1": "fra.1",
    "Brasileirão Série A": "bra.1",
    "Serie A": "ita.1",
    "UEFA Champions League": "uefa.champions",
}

# Data de amanhã em BRT
tomorrow = datetime.now(tz_brt) + timedelta(days=1)
tomorrow_str = tomorrow.strftime("%Y%m%d")

print(f"Buscando partidas para: {tomorrow.strftime('%d/%m/%Y')}")
print("=" * 80)

all_matches = []

for league_name, slug in ESPN_LEAGUES.items():
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates={tomorrow_str}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            continue
        
        events = resp.json().get("events", [])
        for event in events:
            comp = event.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            
            c0, c1 = competitors[0], competitors[1]
            home = c0 if c0.get("homeAway") == "home" else c1
            away = c1 if c0.get("homeAway") == "home" else c0
            
            home_name = home.get("team", {}).get("displayName", "?")
            away_name = away.get("team", {}).get("displayName", "?")
            kickoff = event.get("date", "")
            
            all_matches.append({
                "league": league_name,
                "home": home_name,
                "away": away_name,
                "kickoff": kickoff,
            })
    except Exception:
        continue

print(f"Total de partidas encontradas: {len(all_matches)}")
print()

for i, m in enumerate(all_matches, 1):
    try:
        kt = datetime.fromisoformat(m["kickoff"].replace("Z", "+00:00"))
        kt_brt = kt.astimezone(tz_brt)
        kickoff_fmt = kt_brt.strftime("%d/%m %H:%M")
    except Exception:
        kickoff_fmt = m["kickoff"]
    
    print(f"{i:2}. [{m['league']:25}] {m['home']} vs {m['away']}")
    print(f"    Horário (BRT): {kickoff_fmt}")
    print()