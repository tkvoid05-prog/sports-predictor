import numpy as np
from scipy.stats import poisson, nbinom

def dixon_coles_tau(x: int, y: int, lambda_h: float, mu_a: float, rho: float = -0.11) -> float:
    if x == 0 and y == 0:
        return 1.0 - (lambda_h * mu_a * rho)
    elif x == 0 and y == 1:
        return 1.0 + (lambda_h * rho)
    elif x == 1 and y == 0:
        return 1.0 + (mu_a * rho)
    elif x == 1 and y == 1:
        return 1.0 - rho
    return 1.0

def calculate_score_matrix(lambda_h: float, mu_a: float, max_goals: int = 7, rho: float = -0.11) -> np.ndarray:
    matrix = np.zeros((max_goals + 1, max_goals + 1))
    for x in range(max_goals + 1):
        p_x = poisson.pmf(x, lambda_h)
        for y in range(max_goals + 1):
            p_y = poisson.pmf(y, mu_a)
            adj = dixon_coles_tau(x, y, lambda_h, mu_a, rho)
            matrix[x, y] = max(0.0, p_x * p_y * adj)
            
    total_prob = np.sum(matrix)
    if total_prob > 0:
        matrix /= total_prob
    return matrix

def calc_nbinom_over_under(mean: float, variance: float, line: float) -> dict:
    if variance <= mean:
        k = int(np.floor(line))
        p_under = float(poisson.cdf(k, mean))
        p_over = max(0.01, 1.0 - p_under)
        return {
            "line": line,
            "prob_over": round(p_over * 100, 1),
            "fair_odd_over": round(1.0 / p_over, 2)
        }
    
    p = mean / variance
    n = (mean ** 2) / (variance - mean)
    k = int(np.floor(line))
    p_under = float(nbinom.cdf(k, n, p))
    p_over = max(0.01, 1.0 - p_under)
    
    return {
        "line": line,
        "prob_over": round(p_over * 100, 1),
        "fair_odd_over": round(1.0 / p_over, 2)
    }

def analyze_match_markets(home_stats: dict, away_stats: dict, referee_data: dict = None) -> dict:
    # 1. Regressão à Média e Clipping de Gols
    # Trava entre 0.45 e 2.95 para evitar distorções
    lambda_raw = home_stats.get("attack_strength", 1.0) * away_stats.get("defense_vulnerability", 1.0) * 1.35
    mu_raw = away_stats.get("attack_strength", 1.0) * home_stats.get("defense_vulnerability", 1.0) * 1.05
    
    lambda_h = float(np.clip(lambda_raw, 0.45, 2.95))
    mu_a = float(np.clip(mu_raw, 0.45, 2.70))
    
    matrix = calculate_score_matrix(lambda_h, mu_a)
    
    # Gols
    p_over_1_5 = float(np.sum([matrix[x, y] for x in range(matrix.shape[0]) for y in range(matrix.shape[1]) if x + y > 1.5]))
    p_over_2_5 = float(np.sum([matrix[x, y] for x in range(matrix.shape[0]) for y in range(matrix.shape[1]) if x + y > 2.5]))
    p_btts = float(np.sum(matrix[1:, 1:]))
    
    # Mercado Composto: BTTS OU Over 2.5
    losing_scores = [(0,0), (1,0), (2,0), (0,1), (0,2)]
    p_losing = sum(matrix[x, y] for x, y in losing_scores if x < matrix.shape[0] and y < matrix.shape[1])
    p_btts_or_over25 = float(np.clip(1.0 - p_losing, 0.05, 0.98))
    
    exp_goals = round(lambda_h + mu_a, 2)
    goals_analysis = {
        "expected_total": exp_goals,
        "over_1_5": {"prob_over": round(p_over_1_5 * 100, 1), "fair_odd": round(1.0 / max(p_over_1_5, 0.01), 2)},
        "over_2_5": {"prob_over": round(p_over_2_5 * 100, 1), "fair_odd": round(1.0 / max(p_over_2_5, 0.01), 2)},
        "btts": {"prob_yes": round(p_btts * 100, 1), "fair_odd": round(1.0 / max(p_btts, 0.01), 2)},
        "btts_or_over25": {"prob_hit": round(p_btts_or_over25 * 100, 1), "fair_odd": round(1.0 / p_btts_or_over25, 2)}
    }
    
    # 2. Cantos
    exp_corners = float(np.clip(home_stats.get("avg_corners_for", 5.0) + away_stats.get("avg_corners_for", 4.5), 6.5, 14.5))
    var_corners = exp_corners * 1.35
    corners_analysis = {
        "expected_total": round(exp_corners, 1),
        "over_8_5": calc_nbinom_over_under(exp_corners, var_corners, 8.5),
        "over_9_5": calc_nbinom_over_under(exp_corners, var_corners, 9.5),
        "over_10_5": calc_nbinom_over_under(exp_corners, var_corners, 10.5),
    }
    
    # 3. Finalizações
    exp_shots = round(home_stats.get("avg_shots", 12.0) + away_stats.get("avg_shots", 11.0), 1)
    exp_sot = round(home_stats.get("avg_shots_target", 4.2) + away_stats.get("avg_shots_target", 3.8), 1)
    p_sot_85 = max(0.01, 1.0 - float(poisson.cdf(8, exp_sot)))
    shots_analysis = {
        "expected_shots": exp_shots,
        "expected_sot": exp_sot,
        "over_8_5_sot": {"prob_over": round(p_sot_85 * 100, 1), "fair_odd": round(1.0 / p_sot_85, 2)}
    }
    
    # 4. Cartões Calibrados
    base_cards = home_stats.get("avg_cards", 2.1) + away_stats.get("avg_cards", 2.1)
    ref_factor = 1.0
    if referee_data and referee_data.get("league_avg_cards", 0) > 0:
        ref_factor = float(np.clip(referee_data.get("referee_avg_cards", 4.8) / referee_data["league_avg_cards"], 0.75, 1.35))
    
    exp_cards = float(np.clip(base_cards * ref_factor, 2.0, 7.5))
    p_cards_35 = max(0.01, 1.0 - float(poisson.cdf(3, exp_cards)))
    p_cards_45 = max(0.01, 1.0 - float(poisson.cdf(4, exp_cards)))
    cards_analysis = {
        "expected_total": round(exp_cards, 2),
        "referee_factor": round(ref_factor, 2),
        "over_3_5": {"prob_over": round(p_cards_35 * 100, 1), "fair_odd": round(1.0 / p_cards_35, 2)},
        "over_4_5": {"prob_over": round(p_cards_45 * 100, 1), "fair_odd": round(1.0 / p_cards_45, 2)}
    }
    
    return {
        "goals": goals_analysis,
        "corners": corners_analysis,
        "shots": shots_analysis,
        "cards": cards_analysis
    }