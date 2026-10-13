import numpy as np
from scipy.stats import nbinom, poisson
import logging

logger = logging.getLogger(__name__)

class InsufficientDataError(Exception):
    pass

def calc_fair_odd(prob_pct):
    """Converte probabilidade percentual em odd justa decimal."""
    if prob_pct <= 0 or prob_pct >= 100:
        return 0.0
    return round(100 / prob_pct, 2)

def calc_nbinom_over(mean, variance, line):
    """
    Calcula probabilidade de Over usando Binomial Negativa.
    Fallback para Poisson se a variância for <= média (subdispersão).
    """
    if mean <= 0:
        return 0.0
    
    if variance <= mean:
        # Fallback para Poisson quando não há sobredispersão
        prob_under = poisson.cdf(int(line), mean)
    else:
        # Parametrização da Binomial Negativa a partir de média e variância
        n = (mean ** 2) / (variance - mean)
        p = mean / variance
        # P(X > line) = 1 - P(X <= line)
        prob_under = nbinom.cdf(int(line), n, p)
    
    return round((1 - prob_under) * 100, 1)

def analyze_match_markets(home_stats: dict, away_stats: dict) -> dict:
    h_sample = home_stats.get("sample_size", 0)
    a_sample = away_stats.get("sample_size", 0)
    
    if h_sample < 3 or a_sample < 3:
        raise InsufficientDataError(f"Amostra insuficiente (Home: {h_sample}, Away: {a_sample})")

    # =========================================================================
    # 1. MERCADO DE GOLS (Matriz Dixon-Coles)
    # =========================================================================
    h_goals = home_stats.get("goals_scored", [])
    a_goals = away_stats.get("goals_scored", [])
    
    lambda_h = float(np.mean(h_goals)) if h_goals else 1.2
    mu_a = float(np.mean(a_goals)) if a_goals else 1.2
    
    # Matriz de probabilidade de placares (0 a 5 gols)
    max_goals = 6
    score_matrix = np.zeros((max_goals, max_goals))
    rho = -0.11 # Fator de correlação Dixon-Coles padrão
    
    for i in range(max_goals):
        for j in range(max_goals):
            prob = poisson.pmf(i, lambda_h) * poisson.pmf(j, mu_a)
            # Ajuste Dixon-Coles para placares baixos
            if i == 0 and j == 0:
                prob *= (1 - (lambda_h * mu_a) * rho)
            elif i == 0 and j == 1:
                prob *= (1 + (lambda_h) * rho)
            elif i == 1 and j == 0:
                prob *= (1 + (mu_a) * rho)
            elif i == 1 and j == 1:
                prob *= (1 - rho)
            score_matrix[i, j] = prob

    # Normalizar a matriz para garantir que a soma seja 100%
    score_matrix /= np.sum(score_matrix)

    # Cálculos de Gols (soma de células da matriz)
    p_over_15 = round((1 - np.sum(score_matrix[0:2, 0:2])) * 100, 1)
    p_over_25 = round((1 - np.sum(score_matrix[0:3, 0:3])) * 100, 1)
    
    # BTTS (1 - P(Home 0) - P(Away 0) + P(0-0))
    p_btts = round((1 - np.sum(score_matrix[0, :]) - np.sum(score_matrix[:, 0]) + score_matrix[0, 0]) * 100, 1)
    
    # BTTS ou Over 2.5 (União: 1 - P(Não BTTS E Não Over 2.5))
    # Placares que NÃO são BTTS e NÃO são Over 2.5: 0-0, 1-0, 0-1, 2-0, 0-2
    p_not_btts_and_not_o25 = score_matrix[0, 0] + score_matrix[1, 0] + score_matrix[0, 1] + score_matrix[2, 0] + score_matrix[0, 2]
    p_combo = round((1 - p_not_btts_and_not_o25) * 100, 1)

    # Gols por time individual (Poisson independente)
    p_home_over_15 = round((1 - poisson.cdf(1, lambda_h)) * 100, 1)
    p_away_over_15 = round((1 - poisson.cdf(1, mu_a)) * 100, 1)
    
    # 1X2 (soma de triângulos da matriz)
    p_home_win = round(np.sum(np.tril(score_matrix, -1)) * 100, 1) # i > j
    p_draw = round(np.sum(np.diag(score_matrix)) * 100, 1)          # i == j
    p_away_win = round(np.sum(np.triu(score_matrix, 1)) * 100, 1)   # i < j

    goals_analysis = {
        "expected_total": round(lambda_h + mu_a, 1),
        "lambda_h": round(lambda_h, 2),
        "mu_a": round(mu_a, 2),
        "over_1_5": {"prob": p_over_15, "fair_odd": calc_fair_odd(p_over_15)},
        "over_2_5": {"prob": p_over_25, "fair_odd": calc_fair_odd(p_over_25)},
        "btts": {"prob": p_btts, "fair_odd": calc_fair_odd(p_btts)},
        "btts_or_over25": {"prob": p_combo, "fair_odd": calc_fair_odd(p_combo)},
        "home_over_1_5": {"prob": p_home_over_15, "fair_odd": calc_fair_odd(p_home_over_15)},
        "away_over_1_5": {"prob": p_away_over_15, "fair_odd": calc_fair_odd(p_away_over_15)},
        "home_win_prob": p_home_win,
        "draw_prob": p_draw,
        "away_win_prob": p_away_win,
    }

    # =========================================================================
    # 2. MERCADOS SECUNDÁRIOS (Binomial Negativa com dados reais)
    # =========================================================================
    def process_secondary_market(h_list, a_list, lines):
        if not h_list or not a_list or len(h_list) < 3 or len(a_list) < 3:
            return None
        
        h_mean = float(np.mean(h_list))
        h_var = float(np.var(h_list, ddof=1)) if len(h_list) > 1 else h_mean
        
        a_mean = float(np.mean(a_list))
        a_var = float(np.var(a_list, ddof=1)) if len(a_list) > 1 else a_mean
        
        total_mean = round(h_mean + a_mean, 1)
        total_var = h_var + a_var # Assumindo independência entre os times
        
        market_data = {"expected_total": total_mean}
        for line in lines:
            prob_over = calc_nbinom_over(total_mean, total_var, line)
            # Formata a chave: 8.5 vira "over_8_5"
            line_key = f"over_{str(line).replace('.', '_')}"
            market_data[line_key] = {
                "prob_over": prob_over,
                "fair_odd": calc_fair_odd(prob_over)
            }
        return market_data

    # Linhas de mercado definidas no escopo da FASE 2
    corners_lines = [8.5, 9.5, 10.5]
    shots_lines = [8.5]      # Over 8.5 chutes no alvo (total da partida)
    cards_lines = [3.5, 4.5]

    corners_analysis = process_secondary_market(
        home_stats.get("corners", []), 
        away_stats.get("corners", []), 
        corners_lines
    )
    
    shots_analysis = process_secondary_market(
        home_stats.get("shots_on_target", []), 
        away_stats.get("shots_on_target", []), 
        shots_lines
    )
    
    cards_analysis = process_secondary_market(
        home_stats.get("cards", []), 
        away_stats.get("cards", []), 
        cards_lines
    )

    return {
        "goals": goals_analysis,
        "corners": corners_analysis or {},
        "shots": shots_analysis or {},
        "cards": cards_analysis or {},
        "model_info": {
            "algorithm": "Dixon-Coles Bivariate Poisson + Negative Binomial",
            "rho": rho,
            "home_sample_size": h_sample,
            "away_sample_size": a_sample,
        }
    }