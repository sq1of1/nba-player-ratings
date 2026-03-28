"""
Automated NBA WAR Database Update
Fetches data, calculates WAR, saves to Supabase
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from supabase import create_client, Client

# Import your existing modules
from nba_data_pipeline import NBADataPipeline
from advanced_model import AdvancedModel

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    """Connect to Supabase"""
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_KEY')
    
    if not url or not key:
        logger.error("Missing Supabase credentials!")
        sys.exit(1)
    
    return create_client(url, key)

def fetch_nba_data(max_retries=3):
    """Fetch NBA data with retry logic"""
    pipeline = NBADataPipeline(season="2025-26")
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Fetching NBA data (attempt {attempt}/{max_retries})...")
            time.sleep(2)
            
            df = pipeline.fetch_all_data()
            
            if df is None or len(df) == 0:
                raise ValueError("No data returned")
            
            logger.info(f"Fetched data for {len(df)} players")
            return df
            
        except Exception as e:
            logger.error(f"Attempt {attempt} failed: {e}")
            
            if attempt < max_retries:
                wait_time = 5 * (2 ** (attempt - 1))
                logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                logger.error("All retries failed")
                sys.exit(1)

def calculate_war(df):
    """Calculate WAR ratings"""
    try:
        logger.info("Calculating WAR...")
        model = AdvancedModel()
        ratings_df = model.generate_ratings(df)
        logger.info(f"WAR calculated for {len(ratings_df)} players")
        return ratings_df
    except Exception as e:
        logger.error(f"WAR calculation failed: {e}")
        sys.exit(1)

def save_to_supabase(supabase: Client, ratings_df: pd.DataFrame):
    """Save players and ratings to Supabase"""
    logger.info("Saving to Supabase...")
    
    # Save players
    players = []
    for _, row in ratings_df.iterrows():
        players.append({
            'player_id': str(row.get('PLAYER_ID', '')),
            'player_name': str(row['PLAYER_NAME']),
            'team_abbreviation': str(row.get('TEAM_ABBREVIATION', '')),
            'position': str(row.get('position', '')),
            'position_detail': str(row.get('position_detail', '')),
            'updated_at': datetime.utcnow().isoformat()
        })
    
    # Batch upsert players
    batch_size = 100
    for i in range(0, len(players), batch_size):
        batch = players[i:i + batch_size]
        try:
            supabase.table('players').upsert(batch, on_conflict='player_id').execute()
            logger.info(f"Saved player batch {i//batch_size + 1}")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Failed to save players: {e}")
    
    # Save ratings
    calculation_date = datetime.utcnow().date().isoformat()
    ratings = []
    
    for _, row in ratings_df.iterrows():
        ratings.append({
            'player_id': str(row.get('PLAYER_ID', '')),
            'calculation_date': calculation_date,
            'overall_rating': float(row.get('OVERALL_RATING', 0)),
            'offense_rating': float(row.get('OFFENSE_RATING', 0)),
            'defense_rating': float(row.get('DEFENSE_RATING', 0)),
            'total_war': float(row.get('TOTAL_WAR', 0)),
            'offensive_war': float(row.get('OFFENSIVE_WAR', 0)),
            'defensive_war': float(row.get('DEFENSIVE_WAR', 0)),
            'pts': float(row.get('PTS', 0)),
            'ast': float(row.get('AST', 0)),
            'reb': float(row.get('REB', 0)),
            'stl': float(row.get('STL', 0)),
            'blk': float(row.get('BLK', 0)),
            'tov': float(row.get('TOV', 0)),
            'min': float(row.get('MIN', 0)),
            'gp': int(row.get('GP', 0)),
            'fg_pct': float(row.get('FG_PCT', 0)),
            'fg3_pct': float(row.get('FG3_PCT', 0)),
            'ft_pct': float(row.get('FT_PCT', 0)),
            'ts_pct': float(row.get('TS_PCT', 0)),
            'usg_pct': float(row.get('USG_PCT', 0)),
            'net_rating': float(row.get('NET_RATING', 0)),
            'tier': str(row.get('TIER', 'Unknown')),
            'updated_at': datetime.utcnow().isoformat()
        })
    
    # Batch upsert ratings
    for i in range(0, len(ratings), batch_size):
        batch = ratings[i:i + batch_size]
        try:
            supabase.table('war_ratings').upsert(
                batch, 
                on_conflict='player_id,calculation_date'
            ).execute()
            logger.info(f"Saved ratings batch {i//batch_size + 1}")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Failed to save ratings: {e}")

def cleanup_old_data(supabase: Client, days_to_keep=365):
    """Delete old ratings to save space"""
    logger.info("Cleaning up old data...")
    cutoff_date = (datetime.utcnow() - timedelta(days=days_to_keep)).date().isoformat()
    
    try:
        supabase.table('war_ratings').delete().lt('calculation_date', cutoff_date).execute()
        logger.info("Cleanup complete")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

def main():
    """Main execution"""
    logger.info("=" * 50)
    logger.info("Starting Daily WAR Update")
    logger.info("=" * 50)
    
    # Connect to Supabase
    supabase = get_supabase_client()
    logger.info("Connected to Supabase")
    
    # Fetch and calculate
    df = fetch_nba_data()
    ratings_df = calculate_war(df)
    
    # Save to database
    save_to_supabase(supabase, ratings_df)
    
    # Cleanup
    cleanup_old_data(supabase)
    
    logger.info("=" * 50)
    logger.info("Daily WAR Update Complete!")
    logger.info("=" * 50)

if __name__ == "__main__":
    main()
