import logging
import numpy as np
from scipy.stats import poisson, nbinom
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class InsufficientDataError(Exception):
    """Exceção lançada quando a amostra de jogos é insuficiente para modelagem estatística."""
    pass


def dixon_coles_tau(x: int, y: int, lambda_h: float, mu_a: float, rho: float = -0.11) -> float:
    """
    Função de ajuste de Dixon-Coles para corrigir a subestimação de placares baixos.
    rho = -0.11 é o valor empiricamente validado para futebol.
    """
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
    """
    Gera a matriz de probabilidade bivariada de placares (0-0 até max_goals-max_goals).
    Aplica o ajuste de Dixon-Coles e normaliza para garantir que a soma das probabilidades seja 1.0.
    """
    matrix = np.zeros((max_goals + 1, max_goals + 1))
    
    for x in range(max_goals + 1):
        p_x = poisson.pmf(x, lambda_h)
        for y in range(max_goals + 1):
            p_y = poisson.pmf(y, mu_a)
            adj = dixon_coles_tau(x, y, lambda_h, mu_a, rho)
            # Garante que nenhuma probabilidade seja negativa devido a ajustes numéricos extremos
            matrix[x, y] = max(0.0, p_x * p_y * adj)
            
    total_prob = np.sum(matrix)
    if total_prob > 0:
        matrix /= total_prob
        
    return matrix


def calc_nbinom_over_under(mean: float, variance: float, line: float) -> Optional[Dict[str, Any]]:
    """
    Calcula probabilidades de Over/Under usando Distribuição Binomial Negativa.
    Ideal para mercados com superdispersão (variância > média), como escanteios.
    """
    if variance <= mean or mean <= 0:
        # Fallback seguro para Poisson se não houver superdispersão
        k = int(np.floor(line))
        p_under = float(poisson.cdf(k, mean))
        p_over = max(0.01, 1.0 - p_under)
    else:
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


def analyze_match_markets(home_stats: Dict[str, Any], away_stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Motor principal de análise. Recebe dados brutos reais e retorna probabilidades exatas.
    """
    # 1. Validação de Integridade dos Dados (Defesa em Profundidade)
    h_sample = home_stats.get("sample_size", 0)
    a_sample = away_stats.get("sample_size", 0)
    
    if h_sample < 3 or a_sample < 3:
        raise InsufficientDataError(f"Amostra insuficiente: Home={h_sample}, Away={a_sample}. Mínimo 3 jogos.")

    # 2. Cálculo de Gols Esperados (Lambda e Mu)
    # Estimador robusto: Média entre o ataque do time e a defesa do oponente
    h_scored_mean = float(np.mean(home_stats["goals_scored"]))
    a_conceded_mean = float(np.mean(away_stats["goals_conceded"]))
    lambda_h = float(np.clip((h_scored_mean + a_conceded_mean) / 2.0, 0.3, 3.5))

    a_scored_mean = float(np.mean(away_stats["goals_scored"]))
    h_conceded_mean = float(np.mean(home_stats["goals_conceded"]))
    mu_a = float(np.clip((a_scored_mean + h_conceded_mean) / 2.0, 0.3, 3.5))

    # 3. Geração da Matriz de Probabilidades (Dixon-Coles)
    matrix = calculate_score_matrix(lambda_h, mu_a)

    # 4. Cálculo Exato dos Mercados de Gols a partir da Matriz
    # Over 1.5: Soma de todas as células onde x + y > 1.5
    p_over_1_5 = float(np.sum([matrix[x, y] for x in range(matrix.shape[0]) for y in range(matrix.shape[1]) if x + y > 1.5]))
    
    # Over 2.5: Soma de todas as células onde x + y > 2.5
    p_over_2_5 = float(np.sum([matrix[x, y] for x in range(matrix.shape[0]) for y in range(matrix.shape[1]) if x + y > 2.5]))
    
    # BTTS (Ambas Marcam): Soma da submatriz onde x >= 1 e y >= 1
    p_btts = float(np.sum(matrix[1:, 1:]))
    
    # Combo BTTS ou Over 2.5: 1 - P(Placares que perdem em ambos os critérios)
    # Placares perdedores: 0-0, 1-0, 2-0, 0-1, 0-2
    losing_scores = [(0,0), (1,0), (2,0), (0,1), (0,2)]
    p_losing = sum(matrix[x, y] for x, y in losing_scores if x < matrix.shape[0] and y < matrix.shape[1])
    p_btts_or_over25 = float(np.clip(1.0 - p_losing, 0.05, 0.98))

    goals_analysis = {
        "expected_total": round(lambda_h + mu_a, 2),
        "lambda_h": round(lambda_h, 2), # Exposto para auditoria
        "mu_a": round(mu_a, 2),         # Exposto para auditoria
        "over_1_5": {"prob": round(p_over_1_5 * 100, 1), "fair_odd": round(1.0 / max(p_over_1_5, 0.01), 2)},
        "over_2_5": {"prob": round(p_over_2_5 * 100, 1), "fair_odd": round(1.0 / max(p_over_2_5, 0.01), 2)},
        "btts": {"prob": round(p_btts * 100, 1), "fair_odd": round(1.0 / max(p_btts, 0.01), 2)},
        "btts_or_over25": {"prob": round(p_btts_or_over25 * 100, 1), "fair_odd": round(1.0 / p_btts_or_over25, 2)}
    }

    # 5. Mercados Secundários (Desativados temporariamente por ausência de dados reais na API /schedule)
    # Conforme acordado na Fase 1: Zero alucinação. Retornamos null com motivo explícito.
    secondary_markets_placeholder = {
        "status": "awaiting_real_data",
        "reason": "Endpoint /schedule da ESPN não fornece dados de cantos/chutes/cartões. Coleta via /summary será implementada na Fase 2.",
        "corners": None,
        "shots": None,
        "cards": None
    }

    return {
        "goals": goals_analysis,
        "secondary_markets": secondary_markets_placeholder,
        "model_info": {
            "algorithm": "Dixon-Coles Bivariate Poisson",
            "rho": -0.11,
            "home_sample_size": h_sample,
            "away_sample_size": a_sample
        }
    }