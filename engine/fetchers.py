from datetime import datetime
import requests

ESPN_LEAGUES = {
    "Premier League": "eng.1",
    "La Liga": "esp.1",
    "Bundesliga": "ger.1",
    "Ligue 1": "fra.1",
    "Brasileirão Série A": "bra.1",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_team_last_5_matches(league_slug: str, team_id: str) -> dict:
    """Busca os últimos 5 jogos reais já finalizados de uma equipe na ESPN."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/teams/{team_id}/schedule"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return {
                "goals_scored": [1.2] * 5,
                "goals_conceded": [1.1] * 5,
                "sample_size": 0,
            }

        events = resp.json().get("events", [])
        finished_matches = []

        for ev in events:
            comp = ev.get("competitions", [{}])[0]
            status = comp.get("status", {}).get("type", {}).get("state", "")
            # Considera apenas jogos que já terminaram
            if status == "post":
                finished_matches.append(comp)

        # Pega os 5 jogos mais recentes
        recent_5 = finished_matches[-5:]
        if not recent_5:
            return {
                "goals_scored": [1.2] * 5,
                "goals_conceded": [1.1] * 5,
                "sample_size": 0,
            }

        scored = []
        conceded = []

        for comp in recent_5:
            competitors = comp.get("competitors", [])
            team_score = 0
            opp_score = 0
            for c in competitors:
                s = int(c.get("score", {}).get("value", 0))
                if str(c.get("id")) == str(team_id):
                    team_score = s
                else:
                    opp_score = s
            scored.append(team_score)
            conceded.append(opp_score)

        return {
            "goals_scored": scored,
            "goals_conceded": conceded,
            "sample_size": len(recent_5),
        }
    except Exception:
        return {
            "goals_scored": [1.2] * 5,
            "goals_conceded": [1.1] * 5,
            "sample_size": 0,
        }


def fetch_espn_fixtures() -> list:
    """Busca as partidas reais do dia e extrai os 5 jogos anteriores de cada clube."""
    # Busca pela data do dia em formato UTC
    today_str = datetime.utcnow().strftime("%Y%m%d")
    fixtures = []

    for league_name, slug in ESPN_LEAGUES.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates={today_str}"
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

                c0 = competitors[0]
                c1 = competitors[1]

                home_comp = c0 if c0.get("homeAway") == "home" else c1
                away_comp = c1 if c0.get("homeAway") == "home" else c0

                home_id = str(home_comp.get("id"))
                away_id = str(away_comp.get("id"))
                home_name = home_comp.get("team", {}).get("displayName", "")
                away_name = away_comp.get("team", {}).get("displayName", "")

                officials = comp.get("officials", [])
                referee = (
                    officials[0].get("displayName", "Não divulgado")
                    if officials
                    else "Não divulgado"
                )

                # Busca histórico real dos últimos 5 jogos de cada time
                home_history = fetch_team_last_5_matches(slug, home_id)
                away_history = fetch_team_last_5_matches(slug, away_id)

                fixtures.append({
                    "league": league_name,
                    "home_team": home_name,
                    "away_team": away_name,
                    "kickoff": event.get("date", ""),
                    "referee": referee,
                    "home_history_5": home_history,
                    "away_history_5": away_history,
                })
        except Exception:
            continue

    return fixtures