import numpy as np
from scipy.stats import poisson, nbinom


def dixon_coles_tau(x: int, y: int, lambda_h: float, mu_a: float, rho: float = -0.11) -> float:
    """Fator de ajuste de dependência para placares baixos (Dixon & Coles, 1997)."""
    if x == 0 and y == 0:
        return 1.0 - (lambda_h * mu_a * rho)
    elif x == 0 and y == 1:
        return 1.0 + (lambda_h * rho)
    elif x == 1 and y == 0:
        return 1.0 + (mu_a * rho)
    elif x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


def calculate_score_matrix(lambda_h: float, mu_a: float, max_goals: int = 8, rho: float = -0.11) -> np.ndarray:
    """Gera matriz bivariada de probabilidades de placar exato com ajuste Dixon-Coles."""
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
    """Calcula Over/Under com tratamento de superdispersão para cantos e faltas."""
    if variance <= mean:
        k = int(np.floor(line))
        p_under = float(poisson.cdf(k, mean))
        return {
            "line": line,
            "prob_over": round((1.0 - p_under) * 100, 1),
            "fair_odd_over": round(1.0 / max(1.0 - p_under, 0.01), 2),
        }

    p = mean / variance
    n = (mean**2) / (variance - mean)
    k = int(np.floor(line))
    p_under = float(nbinom.cdf(k, n, p))
    p_over = max(0.001, 1.0 - p_under)

    return {
        "line": line,
        "prob_over": round(p_over * 100, 1),
        "fair_odd_over": round(1.0 / p_over, 2),
    }


def analyze_match_markets(home_stats: dict, away_stats: dict, referee_data: dict = None) -> dict:
    """Motor quantitativo completo com Força Relativa, Dixon-Coles, EV+ e Mercado Composto."""
    # 1. Parâmetros de gols via Força Relativa Relativa à Liga
    lambda_h = home_stats.get("attack_strength", 1.2) * away_stats.get("defense_vulnerability", 1.0) * 1.35
    mu_a = away_stats.get("attack_strength", 1.0) * home_stats.get("defense_vulnerability", 1.0) * 1.05

    matrix = calculate_score_matrix(lambda_h, mu_a)

    # Probabilidades de Gols
    p_over_1_5 = float(np.sum([matrix[x, y] for x in range(matrix.shape[0]) for y in range(matrix.shape[1]) if x + y > 1.5]))
    p_over_2_5 = float(np.sum([matrix[x, y] for x in range(matrix.shape[0]) for y in range(matrix.shape[1]) if x + y > 2.5]))
    p_btts = float(np.sum(matrix[1:, 1:]))

    # Mercado Composto: BTTS OU Over 2.5
    # Perde apenas em: 0-0, 1-0, 2-0, 0-1, 0-2
    losing_scores = [(0, 0), (1, 0), (2, 0), (0, 1), (0, 2)]
    p_losing = sum(matrix[x, y] for x, y in losing_scores if x < matrix.shape[0] and y < matrix.shape[1])
    p_btts_or_over25 = max(0.01, 1.0 - p_losing)

    exp_goals = round(float(lambda_h + mu_a), 2)
    goals_analysis = {
        "expected_total": exp_goals,
        "over_1_5": {"prob_over": round(p_over_1_5 * 100, 1), "fair_odd": round(1.0 / max(p_over_1_5, 0.01), 2)},
        "over_2_5": {"prob_over": round(p_over_2_5 * 100, 1), "fair_odd": round(1.0 / max(p_over_2_5, 0.01), 2)},
        "btts": {"prob_yes": round(p_btts * 100, 1), "fair_odd": round(1.0 / max(p_btts, 0.01), 2)},
        "btts_or_over25": {"prob_hit": round(p_btts_or_over25 * 100, 1), "fair_odd": round(1.0 / p_btts_or_over25, 2)},
    }

    # 2. Escanteios (Correlação com finalizações + superdispersão)
    exp_corners = home_stats.get("avg_corners_for", 5.2) + away_stats.get("avg_corners_for", 4.5)
    var_corners = exp_corners * 1.38
    corners_analysis = {
        "expected_total": round(exp_corners, 1),
        "over_8_5": calc_nbinom_over_under(exp_corners, var_corners, 8.5),
        "over_9_5": calc_nbinom_over_under(exp_corners, var_corners, 9.5),
        "over_10_5": calc_nbinom_over_under(exp_corners, var_corners, 10.5),
    }

    # 3. Finalizações e Finalizações no Alvo
    exp_shots = home_stats.get("avg_shots", 13.0) + away_stats.get("avg_shots", 11.0)
    exp_sot = home_stats.get("avg_shots_target", 4.5) + away_stats.get("avg_shots_target", 3.8)
    p_sot_over_85 = 1.0 - float(poisson.cdf(8, exp_sot))
    shots_analysis = {
        "expected_shots": round(exp_shots, 1),
        "expected_sot": round(exp_sot, 1),
        "over_8_5_sot": {"prob_over": round(p_sot_over_85 * 100, 1), "fair_odd": round(1.0 / max(p_sot_over_85, 0.01), 2)},
    }

    # 4. Faltas
    exp_fouls = home_stats.get("avg_fouls", 13.5) + away_stats.get("avg_fouls", 13.0)
    var_fouls = exp_fouls * 1.25
    fouls_analysis = {
        "expected_total": round(exp_fouls, 1),
        "over_25_5": calc_nbinom_over_under(exp_fouls, var_fouls, 25.5),
        "over_27_5": calc_nbinom_over_under(exp_fouls, var_fouls, 27.5),
    }

    # 5. Cartões com Calibração do Árbitro
    base_cards = home_stats.get("avg_cards", 2.0) + away_stats.get("avg_cards", 2.2)
    ref_factor = 1.0
    if referee_data and referee_data.get("league_avg_cards", 0) > 0:
        ref_factor = referee_data.get("referee_avg_cards", 4.8) / referee_data["league_avg_cards"]

    exp_cards = base_cards * ref_factor
    p_cards_over_35 = 1.0 - float(poisson.cdf(3, exp_cards))
    p_cards_over_45 = 1.0 - float(poisson.cdf(4, exp_cards))
    cards_analysis = {
        "expected_total": round(exp_cards, 2),
        "referee_factor": round(ref_factor, 2),
        "over_3_5": {"prob_over": round(p_cards_over_35 * 100, 1), "fair_odd": round(1.0 / max(p_cards_over_35, 0.01), 2)},
        "over_4_5": {"prob_over": round(p_cards_over_45 * 100, 1), "fair_odd": round(1.0 / max(p_cards_over_45, 0.01), 2)},
    }

    return {
        "goals": goals_analysis,
        "corners": corners_analysis,
        "shots": shots_analysis,
        "fouls": fouls_analysis,
        "cards": cards_analysis,
    }