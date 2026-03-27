"""
NBA WAR Database Updater
Runs daily to calculate WAR ratings and update Supabase
"""

import os
import sys
from datetime import datetime
from supabase import create_client, Client

# Import your existing WAR calculation code
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from advanced_model import calculate_war_ratings  # Adjust this import based on your actual function name

def get_supabase_client() -> Client:
    """Initialize Supabase client from environment variables"""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables")
    
    return create_client(url, key)

def update_database():
    """Main function to calculate WAR and update database"""
    print(f"🏀 Starting WAR calculation at {datetime.now()}")
    
    try:
        # Step 1: Calculate WAR ratings using your existing model
        print("📊 Calculating WAR ratings...")
        df = calculate_war_ratings()  # This should return a DataFrame with player stats
        
        if df is None or df.empty:
            print("⚠️  No data returned from WAR calculation")
            return
        
        print(f"✅ Calculated ratings for {len(df)} players")
        
        # Step 2: Connect to Supabase
        print("🔌 Connecting to Supabase...")
        supabase = get_supabase_client()
        
        # Step 3: Prepare data for insertion
        today = datetime.now().date().isoformat()
        
        # Step 4: Update players table (upsert player info)
        print("👥 Updating players table...")
        players_data = []
        for _, row in df.iterrows():
            players_data.append({
                "player_id": str(row.get("PLAYER_ID", row.get("player_id", ""))),
                "player_name": str(row.get("PLAYER_NAME", row.get("player_name", ""))),
                "team_abbreviation": str(row.get("TEAM_ABBREVIATION", row.get("team", ""))),
                "position": str(row.get("POSITION", row.get("position", ""))),
                "position_detail": str(row.get("POSITION_DETAIL", row.get("position_detail", "")))
            })
        
        # Upsert players (insert or update if exists)
        result = supabase.table("players").upsert(players_data).execute()
        print(f"✅ Updated {len(players_data)} players")
        
        # Step 5: Insert WAR ratings for today
        print("📈 Inserting WAR ratings...")
        war_data = []
        for _, row in df.iterrows():
            war_data.append({
                "player_id": str(row.get("PLAYER_ID", row.get("player_id", ""))),
                "calculation_date": today,
                "overall_rating": float(row.get("Overall_Rating", 0)),
                "offense_rating": float(row.get("Offense_Rating", 0)),
                "defense_rating": float(row.get("Defense_Rating", 0)),
                "total_war": float(row.get("Total_WAR", 0)),
                "offensive_war": float(row.get("Offensive_WAR", 0)),
                "defensive_war": float(row.get("Defensive_WAR", 0)),
                "pts": float(row.get("PTS", 0)),
                "ast": float(row.get("AST", 0)),
                "reb": float(row.get("REB", 0)),
                "stl": float(row.get("STL", 0)),
                "blk": float(row.get("BLK", 0)),
                "tov": float(row.get("TOV", 0)),
                "min": float(row.get("MIN", 0)),
                "gp": int(row.get("GP", 0)),
                "fg_pct": float(row.get("FG_PCT", 0)),
                "fg3_pct": float(row.get("FG3_PCT", 0)),
                "ft_pct": float(row.get("FT_PCT", 0)),
                "ts_pct": float(row.get("TS_PCT", 0)),
                "usg_pct": float(row.get("USG_PCT", 0)),
                "net_rating": float(row.get("NET_RATING", 0)),
                "tier": str(row.get("Tier", ""))
            })
        
        # Insert war ratings (will update if player+date combo already exists due to UNIQUE constraint)
        result = supabase.table("war_ratings").upsert(war_data, on_conflict="player_id,calculation_date").execute()
        print(f"✅ Inserted/updated {len(war_data)} WAR ratings")
        
        print(f"🎉 Database update completed successfully at {datetime.now()}")
        
    except Exception as e:
        print(f"❌ Error during database update: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    update_database()
