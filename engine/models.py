import numpy as np
from scipy.stats import poisson, nbinom


def calc_poisson_over_under(lambda_val: float, line: float) -> dict:
    """Calcula probabilidades de Over/Under para uma dada linha contínua usando Poisson."""
    k = int(np.floor(line))
    prob_under = float(poisson.cdf(k, lambda_val))
    prob_over = float(1.0 - prob_under)
    return {
        "line": line,
        "prob_over": round(prob_over * 100, 1),
        "prob_under": round(prob_under * 100, 1),
    }


def calc_nbinom_over_under(mean: float, variance: float, line: float) -> dict:
    """
    Calcula probabilidades tratando superdispersão (variância > média)
    usando Distribuição Binomial Negativa (ideal para cantos e faltas).
    """
    if variance <= mean:
        # Se não houver superdispersão, recorre ao Poisson padrão
        return calc_poisson_over_under(mean, line)

    # Parametrização nbinom: n (sucessos), p (probabilidade)
    p = mean / variance
    n = (mean**2) / (variance - mean)

    k = int(np.floor(line))
    prob_under = float(nbinom.cdf(k, n, p))
    prob_over = float(1.0 - prob_under)

    return {
        "line": line,
        "prob_over": round(prob_over * 100, 1),
        "prob_under": round(prob_under * 100, 1),
    }


def analyze_match_markets(home_stats: dict, away_stats: dict, referee_data: dict = None) -> dict:
    """
    Processa métricas consolidadas dos dois times e gera as probabilidades
    para todos os mercados solicitados.
    """
    # 1. GOLS (Média esperada combinada)
    exp_goals = (home_stats.get("avg_goals_for", 1.3) + away_stats.get("avg_goals_against", 1.2) +
                 away_stats.get("avg_goals_for", 1.1) + home_stats.get("avg_goals_against", 1.1)) / 2.0

    goals_analysis = {
        "expected_total": round(exp_goals, 2),
        "over_1_5": calc_poisson_over_under(exp_goals, 1.5),
        "over_2_5": calc_poisson_over_under(exp_goals, 2.5),
        "over_3_5": calc_poisson_over_under(exp_goals, 3.5),
    }

    # 2. ESCANTEIOS (Combinado)
    exp_corners = home_stats.get("avg_corners_for", 5.2) + away_stats.get("avg_corners_for", 4.6)
    var_corners = exp_corners * 1.35  # Fator típico de superdispersão para cantos
    corners_analysis = {
        "expected_total": round(exp_corners, 1),
        "over_8_5": calc_nbinom_over_under(exp_corners, var_corners, 8.5),
        "over_9_5": calc_nbinom_over_under(exp_corners, var_corners, 9.5),
        "over_10_5": calc_nbinom_over_under(exp_corners, var_corners, 10.5),
    }

    # 3. CHUTES TOTAIS E NO ALVO
    exp_shots = home_stats.get("avg_shots", 13.0) + away_stats.get("avg_shots", 11.5)
    exp_sot = home_stats.get("avg_shots_target", 4.8) + away_stats.get("avg_shots_target", 4.0)
    shots_analysis = {
        "expected_shots": round(exp_shots, 1),
        "expected_sot": round(exp_sot, 1),
        "over_24_5_shots": calc_poisson_over_under(exp_shots, 24.5),
        "over_8_5_sot": calc_poisson_over_under(exp_sot, 8.5),
    }

    # 4. FALTAS (Geral e Limites de Linhas)
    exp_fouls = home_stats.get("avg_fouls", 13.5) + away_stats.get("avg_fouls", 13.0)
    var_fouls = exp_fouls * 1.25
    fouls_analysis = {
        "expected_total": round(exp_fouls, 1),
        "over_25_5": calc_nbinom_over_under(exp_fouls, var_fouls, 25.5),
        "over_27_5": calc_nbinom_over_under(exp_fouls, var_fouls, 27.5),
    }

    # 5. CARTÕES & PESO DO ÁRBITRO
    base_cards = home_stats.get("avg_cards", 2.1) + away_stats.get("avg_cards", 2.3)
    ref_factor = 1.0

    if referee_data and referee_data.get("league_avg_cards", 0) > 0:
        ref_avg = referee_data.get("referee_avg_cards", referee_data["league_avg_cards"])
        ref_factor = ref_avg / referee_data["league_avg_cards"]

    exp_cards = base_cards * ref_factor
    cards_analysis = {
        "expected_total": round(exp_cards, 2),
        "referee_factor": round(ref_factor, 2),
        "over_3_5": calc_poisson_over_under(exp_cards, 3.5),
        "over_4_5": calc_poisson_over_under(exp_cards, 4.5),
        "over_5_5": calc_poisson_over_under(exp_cards, 5.5),
    }

    return {
        "goals": goals_analysis,
        "corners": corners_analysis,
        "shots": shots_analysis,
        "fouls": fouls_analysis,
        "cards": cards_analysis,
    }