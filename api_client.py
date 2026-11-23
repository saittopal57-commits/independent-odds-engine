
import requests
import streamlit as st
import unicodedata

BASE_URL = "https://v3.football.api-sports.io"


def normalize(text):
    text = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in text if not unicodedata.combining(c)).lower().strip()


def api_get(endpoint, params):
    key = st.secrets.get("API_FOOTBALL_KEY")
    if not key:
        raise ValueError("API anahtarı Streamlit Secrets içinde bulunamadı.")

    response = requests.get(
        f"{BASE_URL}/{endpoint}",
        headers={"x-apisports-key": key},
        params=params,
        timeout=20
    )
    response.raise_for_status()
    data = response.json()

    if data.get("errors"):
        raise ValueError(f"API hatası: {data['errors']}")

    return data.get("response", [])


@st.cache_data(ttl=21600, show_spinner=False)
def search_team(name):
    clean_name = "".join(
        c for c in unicodedata.normalize("NFKD", name)
        if c.isalnum() or c.isspace()
    )
    results = api_get("teams", {"search": clean_name.strip()})

    if not results:
        raise ValueError(f"Takım bulunamadı: {name}")

    target = normalize(name)

    exact = [
        item for item in results
        if normalize(item["team"]["name"]) == target
    ]

    selected = exact[0] if exact else results[0]

    return {
        "id": selected["team"]["id"],
        "name": selected["team"]["name"],
        "country": selected.get("team", {}).get("country", "")
    }


@st.cache_data(ttl=21600, show_spinner=False)
def recent_fixtures(team_id, count=10):
    return api_get(
        "fixtures",
        {"team": team_id, "last": count}
    )


def team_rates(fixtures, team_id, venue):
    games = []

    for item in fixtures:
        fixture = item["fixture"]
        teams = item["teams"]
        goals = item["goals"]

        if fixture["status"]["short"] not in ("FT", "AET", "PEN"):
            continue

        home_id = teams["home"]["id"]
        away_id = teams["away"]["id"]

        if team_id == home_id:
            scored = goals["home"]
            conceded = goals["away"]
            side = "home"
        elif team_id == away_id:
            scored = goals["away"]
            conceded = goals["home"]
            side = "away"
        else:
            continue

        if scored is None or conceded is None:
            continue

        if venue == "all" or venue == side:
            games.append((float(scored), float(conceded)))

    if not games:
        raise ValueError("Gol istatistiği için yeterli maç bulunamadı.")

    return {
        "scored": sum(x[0] for x in games) / len(games),
        "conceded": sum(x[1] for x in games) / len(games),
        "count": len(games)
    }


def estimate_api_lambdas(home_name, away_name):
    home_team = search_team(home_name)
    away_team = search_team(away_name)

    if home_team["id"] == away_team["id"]:
        raise ValueError("Ev sahibi ve deplasman takımı aynı olamaz.")

    home_games = recent_fixtures(home_team["id"])
    away_games = recent_fixtures(away_team["id"])

    home_rates = team_rates(home_games, home_team["id"], "home")
    away_rates = team_rates(away_games, away_team["id"], "away")

    # Rakibin savunma verisi: kendi maç geçmişindeki yenilen goller.
    away_defence = team_rates(away_games, away_team["id"], "away")
    home_defence = team_rates(home_games, home_team["id"], "home")

    baseline_home = 1.35
    baseline_away = 1.10

    raw_home = (home_rates["scored"] + away_defence["conceded"]) / 2
    raw_away = (away_rates["scored"] + home_defence["conceded"]) / 2

    weight_home = min(home_rates["count"], away_defence["count"]) / (
        min(home_rates["count"], away_defence["count"]) + 5
    )
    weight_away = min(away_rates["count"], home_defence["count"]) / (
        min(away_rates["count"], home_defence["count"]) + 5
    )

    lambda_home = (
        weight_home * raw_home + (1 - weight_home) * baseline_home
    )
    lambda_away = (
        weight_away * raw_away + (1 - weight_away) * baseline_away
    )

    return {
        "home_name": home_team["name"],
        "away_name": away_team["name"],
        "lambda_home": round(max(0.05, min(4.5, lambda_home)), 2),
        "lambda_away": round(max(0.05, min(4.5, lambda_away)), 2),
        "home_sample": home_rates["count"],
        "away_sample": away_rates["count"],
        "source": "API-Football son maçları",
        "warning": "İlk sürüm: lig ortalaması, xG ve kadro etkisi henüz modele dahil değildir."
  }
  
