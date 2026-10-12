import logging
import requests
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback de segurança para ambientes Python < 3.9 (embora o alvo seja 3.11)
    from datetime import timezone, timedelta
    ZoneInfo = None

# Configuração básica de logging para rastreabilidade no CI/CD
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

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


def fetch_team_last_5_matches(league_slug: str, team_id: str) -> dict | None:
    """
    Busca os últimos jogos reais já finalizados de uma equipe na ESPN.
    Retorna None se a amostra for insuficiente (< 3 jogos) ou em caso de falha.
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/teams/{team_id}/schedule"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()

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
        
        # Regra de integridade: mínimo de 3 jogos para validade estatística
        if len(recent_5) < 3:
            logger.warning(f"Amostra insuficiente para time ID {team_id} na liga {league_slug}. Encontrados: {len(recent_5)}")
            return None

        scored = []
        conceded = []

        for comp in recent_5:
            competitors = comp.get("competitors", [])
            team_score = 0
            opp_score = 0
            
            for c in competitors:
                # Parsing robusto: previne AttributeError se 'score' for string, int ou None
                score_data = c.get("score")
                if isinstance(score_data, dict):
                    s = int(score_data.get("value", 0))
                elif isinstance(score_data, (int, float)):
                    s = int(score_data)
                else:
                    s = 0
                    
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
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Falha de rede ao buscar histórico do time ID {team_id} ({league_slug}): {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao processar histórico do time ID {team_id} ({league_slug}): {e}")
        return None


def fetch_espn_fixtures() -> list:
    """
    Busca as partidas reais do dia e extrai o histórico de cada clube.
    Descarta partidas onde não seja possível obter dados reais completos de ambos os times.
    """
    # Define o fuso horário de Brasília para capturar jogos noturnos corretamente
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

                c0 = competitors[0]
                c1 = competitors[1]

                home_comp = c0 if c0.get("homeAway") == "home" else c1
                away_comp = c1 if c0.get("homeAway") == "home" else c0

                home_id = str(home_comp.get("id"))
                away_id = str(away_comp.get("id"))
                home_name = home_comp.get("team", {}).get("displayName", "")
                away_name = away_comp.get("team", {}).get("displayName", "")

                officials = comp.get("officials", [])
                referee = officials[0].get("displayName", "Não divulgado") if officials else "Não divulgado"

                # Busca histórico real dos últimos jogos de cada time
                home_history = fetch_team_last_5_matches(slug, home_id)
                away_history = fetch_team_last_5_matches(slug, away_id)

                # Tolerância Zero: se um dos times não tiver dados válidos, a partida é descartada
                if home_history is None or away_history is None:
                    logger.warning(f"Partida descartada (dados insuficientes ou falha na coleta): {home_name} vs {away_name}")
                    continue

                fixtures.append({
                    "league": league_name,
                    "home_team": home_name,
                    "away_team": away_name,
                    "kickoff": event.get("date", ""),
                    "referee": referee,
                    "home_history_5": home_history,
                    "away_history_5": away_history,
                })
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Falha de rede ao buscar jogos da liga {league_name} ({slug}): {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao processar liga {league_name} ({slug}): {e}")

    return fixtures