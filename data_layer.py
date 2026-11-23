import pandas as pd

REQUIRED_COLUMNS = ["date", "league", "home_team", "away_team", "home_goals", "away_goals"]

def load_matches(file_or_path) -> pd.DataFrame:
    df = pd.read_csv(file_or_path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("Eksik sütunlar: " + ", ".join(missing))
    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
    for c in ("home_goals", "away_goals"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["date", "league", "home_team", "away_team", "home_goals", "away_goals"])
    df = df[(df.home_goals >= 0) & (df.away_goals >= 0)]
    for c in ("home_xg", "away_xg"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)

def league_baseline(df: pd.DataFrame, league: str):
    d = df[df.league == league]
    if len(d) < 10:
        raise ValueError(f"{league} için en az 10 maç gerekli; bulunan: {len(d)}")
    return float(d.home_goals.mean()), float(d.away_goals.mean())

def _team_rate(rows, goals_col, xg_col, prior_mean, prior_matches=5, recent_n=10):
    rows = rows.sort_values("date").tail(recent_n)
    if rows.empty:
        return prior_mean
    goals = rows[goals_col].astype(float)
    if xg_col in rows.columns and rows[xg_col].notna().any():
        xg = rows[xg_col].astype(float)
        # Blend observed goals and xG where xG exists; fall back to goals per row otherwise.
        vals = goals.copy()
        mask = xg.notna()
        vals.loc[mask] = 0.5 * goals.loc[mask] + 0.5 * xg.loc[mask]
        rate = float(vals.mean())
    else:
        rate = float(goals.mean())
    n = len(rows)
    return (rate * n + prior_mean * prior_matches) / (n + prior_matches)

def estimate_lambdas(df: pd.DataFrame, league: str, home_team: str,
                     away_team: str, recent_n: int = 10):
    d = df[df.league == league].copy()
    if len(d) < 10:
        raise ValueError("Lig için en az 10 geçmiş maç bulunmalı.")
    league_home = float(d.home_goals.mean())
    league_away = float(d.away_goals.mean())

    home_home = d[d.home_team == home_team]
    away_away = d[d.away_team == away_team]
    home_away_def = d[d.away_team == home_team]
    away_home_def = d[d.home_team == away_team]

    home_attack = _team_rate(home_home, "home_goals", "home_xg", league_home, recent_n=recent_n)
    away_defence = _team_rate(away_away, "home_goals", "home_xg", league_home, recent_n=recent_n)
    away_attack = _team_rate(away_away, "away_goals", "away_xg", league_away, recent_n=recent_n)
    home_defence = _team_rate(home_home, "away_goals", "away_xg", league_away, recent_n=recent_n)

    # Ratios are shrunk toward league averages before combining attack and opposing defence.
    h_attack_ratio = home_attack / league_home if league_home else 1.0
    a_def_ratio = away_defence / league_home if league_home else 1.0
    a_attack_ratio = away_attack / league_away if league_away else 1.0
    h_def_ratio = home_defence / league_away if league_away else 1.0

    lambda_home = league_home * (h_attack_ratio * a_def_ratio) ** 0.5
    lambda_away = league_away * (a_attack_ratio * h_def_ratio) ** 0.5
    return {
        "lambda_home": max(0.05, min(4.5, lambda_home)),
        "lambda_away": max(0.05, min(4.5, lambda_away)),
        "league_home_avg": league_home,
        "league_away_avg": league_away,
        "matches_in_league": len(d),
        "home_team_home_matches": len(home_home),
        "away_team_away_matches": len(away_away),
    }

def available_leagues(df):
    return sorted(df.league.dropna().astype(str).unique().tolist())

def available_teams(df, league):
    d = df[df.league == league]
    return sorted(set(d.home_team.astype(str)) | set(d.away_team.astype(str)))
