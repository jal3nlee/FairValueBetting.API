import os
import uuid
import requests
from datetime import datetime, timezone
from supabase import create_client, Client

# Load secrets from GitHub Actions
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Connect to Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

# ✅ For each market, insert a snapshot row
for market_key in markets:
    snapshot_id = str(uuid.uuid4())

    supabase.table("odds_snapshots").insert({
        "id": snapshot_id,
        "market": market_key,
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "payload": data,       # store full API payload for traceability
        "sport": "NFL",
        "region": "us"
    }).execute()

    # Insert odds_lines linked to this snapshot
    for game in data:
        event_id = game["id"]
        commence_time = game["commence_time"]
        home_team = game.get("home_team")
        away_team = game.get("away_team")

        for book in game.get("bookmakers", []):
            book_key = book["key"]

            for market in book.get("markets", []):
                if market["key"] != market_key:
                    continue  # only insert lines for the snapshot's market

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

print(f"Inserted {rows_inserted} rows into odds_lines across {len(markets)} snapshots")
