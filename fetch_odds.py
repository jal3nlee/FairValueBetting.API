import os
import requests
import json
from supabase import create_client, Client

# Load secrets from GitHub Actions
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Connect to Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Example pull: NFL odds (H2H)
url = f"https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
params = {
    "apiKey": ODDS_API_KEY,
    "regions": "us",          # sportsbooks region
    "markets": "h2h",         # moneyline
    "oddsFormat": "american"  # American odds
}

print("Fetching odds...")
resp = requests.get(url, params=params)

if resp.status_code != 200:
    print("Error:", resp.status_code, resp.text)
    exit(1)

data = resp.json()

# Save into Supabase (replace 'odds_lines' with your table name)
for game in data:
    supabase.table("odds_lines").insert({
        "event_id": game["id"],
        "commence_time": game["commence_time"],
        "sport": "NFL",
        "market": "h2h",
        "book": game["bookmakers"][0]["key"] if game["bookmakers"] else None,
        "created_at": "now()"
    }).execute()

print(f"Inserted {len(data)} rows into Supabase")
