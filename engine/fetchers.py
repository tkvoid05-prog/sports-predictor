import logging
import requests
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from datetime import timezone, timedelta
    ZoneInfo = None

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ESPN_LEAGUES = {
    "Premier League": "eng.1",
    "La Liga": "esp.1",
    "Bundesliga": "ger.1",
    "Ligue 1": "fra.1",
    "Brasileirão Série A": "bra.1",
    "Serie A": "ita.1",
    "UEFA Champions League": "uefa.champions",
}

TEAM_DOMESTIC_LEAGUE = {
    "Arsenal": "eng.1", "Manchester United": "eng.1",
    "Atlético Madrid": "esp.1", "Barcelona": "esp.1", "Villarreal": "esp.1",
    "Bayern Munich": "ger.1", "RB Leipzig": "ger.1",
    "Napoli": "ita.1", "Internazionale": "ita.1",
    "Lille": "fra.1", "Lens": "fra.1",
    "Sporting CP": "por.1",
    "Galatasaray": "tur.1",
    "PSV Eindhoven": "ned.1",
    "Club Brugge": "bel.1",
    "Viking FK": "nor.1",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def safe_float(value, default=0.0):
    if value is None:
        return default
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return default

def fetch_team_recent_stats(league_slug: str, team_id: str, team_name: str) -> dict | None:
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/teams/{team_id}/schedule"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        events = resp.json().get("events", [])
        
        finished_matches = [
            ev for ev in events
            if ev.get("competitions", [{}])[0].get("status", {}).get("type", {}).get("state") == "post"
        ]
        
        recent_5 = finished_matches[-5:]
        if len(recent_5) < 3:
            logger.warning(f"Amostra insuficiente para {team_name} em {league_slug}. Encontrados: {len(recent_5)}")
            return None

        goals_scored, goals_conceded = [], []
        corners, shots, shots_on_target, cards = [], [], [], []

        for ev in recent_5:
            comp = ev.get("competitions", [{}])[0]
            event_id = str(ev.get("id"))
            competitors = comp.get("competitors", [])
            
            team_comp = next((c for c in competitors if str(c.get("id")) == str(team_id)), {})
            is_home = team_comp.get("homeAway") == "home"
            
            team_score, opp_score = 0, 0
            for c in competitors:
                score_data = c.get("score")
                s = int(score_data.get("value", 0)) if isinstance(score_data, dict) else int(score_data or 0)
                if str(c.get("id")) == str(team_id):
                    team_score = s
                else:
                    opp_score = s
            goals_scored.append(team_score)
            goals_conceded.append(opp_score)

            try:
                summary_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/summary?event={event_id}"
                sum_resp = requests.get(summary_url, headers=HEADERS, timeout=10)
                if sum_resp.status_code == 200:
                    sum_data = sum_resp.json()
                    box_teams = sum_data.get("boxscore", {}).get("teams", [])
                    team_stats = next((t.get("statistics", []) for t in box_teams if str(t.get("team", {}).get("id")) == str(team_id)), [])
                    
                    def get_stat(name):
                        for stat in team_stats:
                            if stat.get("name") == name:
                                return safe_float(stat.get("displayValue"))
                        return 0.0

                    corners.append(get_stat("wonCorners"))
                    shots.append(get_stat("totalShots"))
                    shots_on_target.append(get_stat("shotsOnTarget"))
                    y_cards = get_stat("yellowCards")
                    r_cards = get_stat("redCards")
                    cards.append(y_cards + r_cards)
                else:
                    logger.warning(f"Summary falhou (HTTP {sum_resp.status_code}) para evento {event_id}")
            except Exception as e:
                logger.warning(f"Erro ao buscar summary do evento {event_id}: {e}")

        return {
            "team_name": team_name,
            "is_home_context": is_home,
            "goals_scored": goals_scored,
            "goals_conceded": goals_conceded,
            "corners": corners,
            "shots": shots,
            "shots_on_target": shots_on_target,
            "cards": cards,
            "sample_size": len(recent_5),
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Falha de rede ao buscar histórico de {team_name} ({league_slug}): {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao processar histórico de {team_name} ({league_slug}): {e}")
        return None

def fetch_espn_fixtures() -> list:
    if ZoneInfo:
        tz_brt = ZoneInfo("America/Sao_Paulo")
    else:
        tz_brt = timezone(timedelta(hours=-3), "BRT")
        
    today_str = datetime.now(tz_brt).strftime("%Y%m%d")
    fixtures = []

    for league_name, slug in ESPN_LEAGUES.items():
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates={today_str}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            events = resp.json().get("events", [])
            
            for event in events:
                comp = event.get("competitions", [{}])[0]
                competitors = comp.get("competitors", [])
                if len(competitors) < 2:
                    continue

                c0, c1 = competitors[0], competitors[1]
                home_comp = c0 if c0.get("homeAway") == "home" else c1
                away_comp = c1 if c0.get("homeAway") == "home" else c0

                home_id = str(home_comp.get("id"))
                away_id = str(away_comp.get("id"))
                home_name = home_comp.get("team", {}).get("displayName", "")
                away_name = away_comp.get("team", {}).get("displayName", "")
                referee = comp.get("officials", [{}])[0].get("displayName", "Não divulgado") if comp.get("officials") else "Não divulgado"

                home_league = TEAM_DOMESTIC_LEAGUE.get(home_name, slug)
                away_league = TEAM_DOMESTIC_LEAGUE.get(away_name, slug)

                home_stats = fetch_team_recent_stats(home_league, home_id, home_name)
                away_stats = fetch_team_recent_stats(away_league, away_id, away_name)

                if home_stats is None or away_stats is None:
                    logger.warning(f"Partida descartada (dados insuficientes): {home_name} vs {away_name}")
                    continue

                fixtures.append({
                    "league": league_name,
                    "home_team": home_name,
                    "away_team": away_name,
                    "kickoff": event.get("date", ""),
                    "referee": referee,
                    "home_stats": home_stats,
                    "away_stats": away_stats,
                })
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Falha de rede ao buscar jogos da liga {league_name} ({slug}): {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao processar liga {league_name} ({slug}): {e}")

    return fixtures