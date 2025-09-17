import os
import uuid
import requests
from supabase import create_client, Client

# Load secrets from GitHub Actions
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Connect to Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Generate one snapshot_id per run
snapshot_id = str(uuid.uuid4())

# Insert snapshot into odds_snapshots (minimal fields only)
supabase.table("odds_snapshots").insert({
    "id": snapshot_id,
    "sport": "NFL"
}).execute()

# Markets to pull
markets = ["h2h", "spreads", "totals"]

url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
params = {
    "apiKey": ODDS_API_KEY,
    "regions": "us",
    "markets": ",".join(markets),
    "oddsFormat": "american"
}

print("Fetching odds...")
resp = requests.get(url, params=params)

if resp.status_code != 200:
    print("Error:", resp.status_code, resp.text)
    exit(1)

data = resp.json()

rows_inserted = 0

for game in data:
    event_id = game["id"]
    commence_time = game["commence_time"]
    home_team = game.get("home_team")
    away_team = game.get("away_team")

    for book in game.get("bookmakers", []):
        book_key = book["key"]

        for market in book.get("markets", []):
            market_key = market["key"]

            for outcome in market.get("outcomes", []):
                name = outcome.get("name")

                # Map outcome name -> enum-friendly side
                if name in ["Over", "Under"]:
                    side = name.lower()
                elif name == home_team:
                    side = "home"
                elif name == away_team:
                    side = "away"
                else:
                    side = None

                line = outcome.get("point")
                price = outcome.get("price")

                supabase.table("odds_lines").insert({
                    "snapshot_id": snapshot_id,
                    "event_id": event_id,
                    "commence_time": commence_time,
                    "home_team": home_team,
                    "away_team": away_team,
                    "book": book_key,
                    "sport": "NFL",
                    "market": market_key,
                    "side": side,
                    "line": line,
                    "price": price
                }).execute()

                rows_inserted += 1

print(f"Inserted {rows_inserted} rows into odds_lines with snapshot_id {snapshot_id}")

