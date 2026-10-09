import io
from datetime import datetime
import pandas as pd
import requests

# Mapeamento oficial dos CSVs de football-data.co.uk (Ligas Europeias)
LEAGUE_URLS = {
    "Premier League": "https://www.football-data.co.uk/mmz4281/2425/E0.csv",
    "La Liga": "https://www.football-data.co.uk/mmz4281/2425/SP1.csv",
    "Bundesliga": "https://www.football-data.co.uk/mmz4281/2425/D1.csv",
    "Ligue 1": "https://www.football-data.co.uk/mmz4281/2425/F1.csv",
}

# Endpoint público e sem bloqueio da ESPN para o Brasileirão Série A
ESPN_BRAZIL_API = "https://site.api.espn.com/apis/site/v2/sports/soccer/bra.1/scoreboard"


def fetch_european_league_data(league_name: str) -> pd.DataFrame:
    """Descarrega os dados históricos consolidados de uma liga europeia específica."""
    url = LEAGUE_URLS.get(league_name)
    if not url:
        return pd.DataFrame()

    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code == 200:
        df = pd.read_csv(io.StringIO(response.text))
        # Filtra apenas colunas essenciais para performance e memória
        cols = [
            "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG",
            "HS", "AS", "HST", "AST", "HF", "AF",
            "HC", "AC", "HY", "AY", "HR", "AR", "Referee"
        ]
        available_cols = [c for c in cols if c in df.columns]
        return df[available_cols].dropna(subset=["HomeTeam", "AwayTeam"])
    return pd.DataFrame()


def fetch_espn_fixtures(target_date: str = None) -> list:
    """Obtém jogos agendados e dados de arbitragem via ESPN para o Brasileirão."""
    params = {}
    if target_date:
        params["dates"] = target_date.replace("-", "")

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(ESPN_BRAZIL_API, headers=headers, params=params, timeout=15)
        if response.status_code != 200:
            return []
        data = response.json()
        events = data.get("events", [])
        fixtures = []

        for ev in events:
            competition = ev.get("competitions", [{}])[0]
            competitors = competition.get("competitors", [])
            home_team = next((c["team"]["name"] for c in competitors if c.get("homeAway") == "home"), "Desconhecido")
            away_team = next((c["team"]["name"] for c in competitors if c.get("homeAway") == "away"), "Desconhecido")

            # Identifica o árbitro escalado (se já divulgado)
            officials = competition.get("officials", [])
            referee_name = officials[0].get("displayName", "Não divulgado") if officials else "Não divulgado"

            # Formata o horário do jogo
            date_str = competition.get("date", "")
            fixtures.append({
                "league": "Brasileirão Série A",
                "home_team": home_team,
                "away_team": away_team,
                "kickoff": date_str,
                "referee": referee_name
            })
        return fixtures
    except Exception:
        return []