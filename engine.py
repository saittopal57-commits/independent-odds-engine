from math import exp, factorial
from typing import Dict, List, Tuple

def poisson_pmf(k: int, lam: float) -> float:
    if lam < 0:
        raise ValueError("Gol beklentisi negatif olamaz.")
    if lam == 0:
        return 1.0 if k == 0 else 0.0
    return exp(-lam) * (lam ** k) / factorial(k)

def poisson_series(lam: float, max_goals: int = 12) -> List[float]:
    return [poisson_pmf(k, lam) for k in range(max_goals + 1)]

def score_matrix(lambda_home: float, lambda_away: float,
                 max_goals: int = 8, rho: float = 0.0) -> List[List[float]]:
    """Independent Poisson score grid with optional Dixon-Coles low-score correction."""
    if not (0 <= rho <= 0.25 or -0.25 <= rho < 0):
        raise ValueError("rho -0.25 ile 0.25 arasında olmalı.")
    h = poisson_series(lambda_home, max_goals)
    a = poisson_series(lambda_away, max_goals)
    matrix = []
    for i in range(max_goals + 1):
        row = []
        for j in range(max_goals + 1):
            p = h[i] * a[j]
            if i == 0 and j == 0:
                tau = 1 - lambda_home * lambda_away * rho
            elif i == 0 and j == 1:
                tau = 1 + lambda_home * rho
            elif i == 1 and j == 0:
                tau = 1 + lambda_away * rho
            elif i == 1 and j == 1:
                tau = 1 - rho
            else:
                tau = 1.0
            row.append(max(0.0, p * tau))
        matrix.append(row)
    return matrix

def analyze_match(lambda_home: float, lambda_away: float,
                  max_goals: int = 8, rho: float = 0.0) -> Dict:
    if lambda_home < 0 or lambda_away < 0:
        raise ValueError("Gol beklentileri negatif olamaz.")
    matrix = score_matrix(lambda_home, lambda_away, max_goals, rho)
    # Normalize displayed score grid to account for the tiny probability mass outside the grid.
    grid_total = sum(sum(row) for row in matrix)
    normalized = [[p / grid_total for p in row] for row in matrix]
    scores = []
    for home in range(max_goals + 1):
        for away in range(max_goals + 1):
            scores.append((home, away, normalized[home][away]))
    scores.sort(key=lambda x: x[2], reverse=True)

    # Exact total-goals distribution for independent Poisson variables.
    total_lam = lambda_home + lambda_away
    total = poisson_series(total_lam, 20)
    p_over = {}
    for line in (0.5, 1.5, 2.5, 3.5, 4.5):
        p_over[line] = sum(total[int(line) + 1:])  # e.g. >2.5 means 3+
    p_under = {line: 1.0 - p for line, p in p_over.items()}

    home_dist = poisson_series(lambda_home, 20)
    away_dist = poisson_series(lambda_away, 20)
    home_over = {line: sum(home_dist[int(line)+1:]) for line in (0.5, 1.5, 2.5)}
    away_over = {line: sum(away_dist[int(line)+1:]) for line in (0.5, 1.5, 2.5)}
    btts_yes = (1 - exp(-lambda_home)) * (1 - exp(-lambda_away))

    return {
        "lambda_home": lambda_home,
        "lambda_away": lambda_away,
        "lambda_total": total_lam,
        "over": p_over,
        "under": p_under,
        "btts_yes": btts_yes,
        "btts_no": 1 - btts_yes,
        "home_over": home_over,
        "away_over": away_over,
        "top_scores": scores[:10],
        "score_matrix": normalized,
        "grid_mass_before_normalization": grid_total,
    }

def fair_odds(probability: float) -> float:
    if probability <= 0:
        return float("inf")
    return 1.0 / probability

def expected_value(probability: float, offered_odds: float) -> float:
    """Expected net return per unit stake; offered odds are post-model only."""
    if offered_odds <= 1:
        raise ValueError("Sunulan oran 1'den büyük olmalı.")
    return probability * offered_odds - 1.0
