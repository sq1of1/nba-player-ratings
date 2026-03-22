"""
NBA Data Pipeline - Foundation
Fetches player stats, processes them, and prepares for analysis
"""

from nba_api.stats.endpoints import (
    playergamelog,
    leaguedashplayerstats,
    commonplayerinfo,
    playerdashboardbyyearoveryear
)
from nba_api.stats.static import players
import pandas as pd
import numpy as np
from datetime import datetime
import time
import json
import os


class NBADataPipeline:
    """
    Main pipeline for fetching and processing NBA data
    """
    
    def __init__(self, season="2025-26"):
        """
        Initialize pipeline
        
        Args:
            season: NBA season in format "2024-25"
        """
        self.season = season
        self.cache_dir = "data/cache"
        self._ensure_directories()
        
    def get_onoff_defensive_impact(self, season=None):
        """
        Fetch ON/OFF court defensive impact for all players
        This shows how much better/worse team defense is when player is on court
        
        Returns:
            DataFrame with player_id and defensive_impact (positive = good defender)
        """
        if season is None:
            season = self.season
            
        print(f"\nAttempting to fetch ON/OFF court splits for {season}...")
        print("This may take a few minutes due to API rate limits...")
        
        try:
            from nba_api.stats.endpoints import leaguedashplayerstats
            import time
            
            # Fetch player stats with splits
            time.sleep(1)
            
            # Get defensive stats with on-court context
            # We'll use the difference in defensive rating as a proxy
            # This is available in the advanced stats
            
            stats = leaguedashplayerstats.LeagueDashPlayerStats(
                season=season,
                measure_type_detailed_defense='Advanced'
            )
            
            df = stats.get_data_frames()[0]
            
            # Create impact metric
            # Players with low DEF_RATING (good) and high minutes = high impact
            # This is a simplified version - true ON/OFF would require team-level data
            
            onoff_impact = pd.DataFrame()
            onoff_impact['PLAYER_ID'] = df['PLAYER_ID']
            onoff_impact['PLAYER_NAME'] = df['PLAYER_NAME']
            
            # Simplified impact: inverse of defensive rating weighted by minutes
            # Good defenders have low DEF_RATING, so invert it
            onoff_impact['DEF_IMPACT'] = (120 - df['DEF_RATING']) * (df['MIN'] / 48)
            
            print(f"  Fetched defensive impact metrics for {len(onoff_impact)} players")
            print("  Note: Using simplified impact metric (true ON/OFF requires team splits)")
            
            return onoff_impact
            
        except Exception as e:
            print(f"  ✗ Could not fetch ON/OFF data: {e}")
            print("  Falling back to stat-based composite only")
            return None
    
    def _ensure_directories(self):
        """Create necessary directories"""
        import os
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs("data/processed", exist_ok=True)
        os.makedirs("data/raw", exist_ok=True)
    
    def calculate_opponent_strength(self, df):
        """
        Estimate opponent strength based on minutes and usage
        Stars face tougher defensive assignments
        
        Returns:
            Series with opponent strength adjustment (0.8 to 1.2)
        """
        # High minutes + high usage = facing tough opponents
        minutes_factor = (df['MIN'] / df['MIN'].max()).clip(0.5, 1.0)
        usage_factor = (df.get('USG_PCT', 20) / 30).clip(0.5, 1.0)
        
        # Combine - stars get 1.1-1.2x, role players get 0.8-0.9x
        opponent_strength = (minutes_factor * 0.6 + usage_factor * 0.4) + 0.5
        
        return opponent_strength.clip(0.8, 1.2)
        """Create necessary directories"""
        import os
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs("data/processed", exist_ok=True)
        os.makedirs("data/raw", exist_ok=True)
        
    def get_all_players(self):
        """
        Get list of all NBA players
        
        Returns:
            DataFrame with player info
        """
        print("Fetching all players...")
        all_players = players.get_players()
        df = pd.DataFrame(all_players)
        
        # Save to cache
        cache_file = f"{self.cache_dir}/all_players.csv"
        df.to_csv(cache_file, index=False)
        print(f"Saved {len(df)} players to {cache_file}")
        
        return df
    
    def find_player(self, player_name):
        """
        Find a player by name
        
        Args:
            player_name: Player's name (first or last)
            
        Returns:
            List of matching players
        """
        all_players = players.find_players_by_full_name(player_name)
        if not all_players:
            # Try partial match
            all_players_list = players.get_players()
            matches = [p for p in all_players_list 
                      if player_name.lower() in p['full_name'].lower()]
            return matches
        return all_players
    
    def get_player_season_stats(self, player_id, season=None):
        """
        Get player's season statistics
        
        Args:
            player_id: NBA player ID
            season: Season (defaults to pipeline season)
            
        Returns:
            DataFrame with player stats
        """
        if season is None:
            season = self.season
            
        print(f"Fetching season stats for player {player_id}, season {season}...")
        
        # Add delay to respect rate limits
        time.sleep(0.6)
        
        stats = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            per_mode_detailed='PerGame'
        )
        
        df = stats.get_data_frames()[0]
        player_df = df[df['PLAYER_ID'] == player_id]
        
        return player_df
    
    def get_league_stats(self, season=None, per_mode='PerGame'):
        """
        Get league-wide player statistics
        
        Args:
            season: Season (defaults to pipeline season)
            per_mode: 'PerGame', 'Per36', 'Per100Possessions', 'Totals'
            
        Returns:
            DataFrame with all player stats
        """
        if season is None:
            season = self.season
            
        print(f"Fetching league stats for {season}, mode: {per_mode}...")
        
        time.sleep(0.6)
        
        stats = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            per_mode_detailed=per_mode
        )
        
        df = stats.get_data_frames()[0]
        
        # Save to cache
        cache_file = f"{self.cache_dir}/league_stats_{season}_{per_mode}.csv"
        df.to_csv(cache_file, index=False)
        print(f"Saved {len(df)} player records to {cache_file}")
        
        return df
    
    def get_advanced_stats(self, season=None):
        """
        Get advanced statistics for all players
        
        Args:
            season: Season (defaults to pipeline season)
            
        Returns:
            DataFrame with advanced stats
        """
        if season is None:
            season = self.season
            
        print(f"Fetching advanced stats for {season}...")
        
        time.sleep(0.6)
        
        stats = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            measure_type_detailed_defense='Advanced'
        )
        
        df = stats.get_data_frames()[0]
        
        # Save to cache
        cache_file = f"{self.cache_dir}/advanced_stats_{season}.csv"
        df.to_csv(cache_file, index=False)
        print(f"Saved advanced stats to {cache_file}")
        
        return df
    
    def calculate_percentiles(self, df, stats_columns):
        """
        Calculate percentile rankings for specified stats
        
        Args:
            df: DataFrame with player stats
            stats_columns: List of column names to rank
            
        Returns:
            DataFrame with added percentile columns
        """
        df = df.copy()
        
        for col in stats_columns:
            if col in df.columns:
                percentile_col = f"{col}_PERCENTILE"
                df[percentile_col] = df[col].rank(pct=True) * 100
                
        return df
    
    def filter_qualified_players(self, df, min_games=10, min_minutes=10):
        """
        Filter to qualified players based on games and minutes
        
        Args:
            df: DataFrame with player stats
            min_games: Minimum games played
            min_minutes: Minimum minutes per game
            
        Returns:
            Filtered DataFrame
        """
        qualified = df[
            (df['GP'] >= min_games) & 
            (df['MIN'] >= min_minutes)
        ].copy()
        
        print(f"Filtered to {len(qualified)} qualified players "
              f"(min {min_games} games, {min_minutes} MPG)")
        
        return qualified
    
    def create_master_dataset(self, season=None):
        """
        Create a master dataset combining multiple stat types
        
        Args:
            season: Season (defaults to pipeline season)
            
        Returns:
            Combined DataFrame
        """
        if season is None:
            season = self.season
            
        print(f"\n{'='*60}")
        print(f"Creating master dataset for {season}")
        print(f"{'='*60}\n")
        
        # Get different stat types
        per_game = self.get_league_stats(season, 'PerGame')
        per_100 = self.get_league_stats(season, 'Per100Possessions')
        advanced = self.get_advanced_stats(season)
        
        # Merge datasets
        master = per_game.copy()
        
        # Merge datasets
        master = per_game.copy()
        
        # Load manual position overrides from CSV
        manual_positions_file = "data/manual_positions.csv"
        if os.path.exists(manual_positions_file):
            manual_positions = pd.read_csv(manual_positions_file)
            
            # Strip whitespace from both columns
            manual_positions['PLAYER_NAME'] = manual_positions['PLAYER_NAME'].str.strip()
            manual_positions['POSITION'] = manual_positions['POSITION'].str.strip()
            
            print(f"  Loaded {len(manual_positions)} manual position entries")
            
            # Merge manual positions
            master = master.merge(
                manual_positions[['PLAYER_NAME', 'POSITION']], 
                on='PLAYER_NAME', 
                how='left'
            )
            
            # Map positions to simplified categories
            def map_position_simple(pos):
                """Map NBA.com position (G, G-F, F, F-C, C) to 5 categories"""
                if pd.isna(pos):
                    return None
                pos = str(pos).strip().upper()
                
                # Keep all 5 position types distinct
                if pos in ['G', 'PG', 'SG']:
                    return 'Guard'
                elif pos in ['G-F']:
                    return 'Wing'  # Combo guards/wings
                elif pos in ['F', 'SF', 'PF']:
                    return 'Forward'
                elif pos in ['F-C']:
                    return 'Combo Big'  # Stretch bigs
                elif pos in ['C']:
                    return 'Big'
                else:
                    return None
            
            master['position'] = master['POSITION'].apply(map_position_simple)
            master['position_detail'] = master['POSITION']  # Keep original (G, G-F, F, F-C, C)
            
            # Count how many got positions
            has_position = master['position'].notna().sum()
            print(f"  Positions assigned: {has_position}/{len(master)} players")
            print(f"  Will use stat-based classification for remaining {len(master) - has_position} players")
        else:
            print(f"  No manual positions file found, will use stat-based classification")
        
        # Add per 100 possessions (with suffix)
        per_100_subset = per_100[['PLAYER_ID', 'PTS', 'AST', 'REB', 'STL', 'BLK', 'TOV']]
        per_100_subset.columns = ['PLAYER_ID'] + [f"{col}_PER100" for col in per_100_subset.columns[1:]]
        master = master.merge(per_100_subset, on='PLAYER_ID', how='left')
        
        # Add advanced stats
        advanced_cols = ['PLAYER_ID', 'OFF_RATING', 'DEF_RATING', 'NET_RATING', 
                        'AST_PCT', 'REB_PCT', 'TS_PCT', 'USG_PCT', 'PIE']
        advanced_subset = advanced[advanced_cols]
        master = master.merge(advanced_subset, on='PLAYER_ID', how='left')
        
        # Calculate percentiles for key stats
        key_stats = ['PTS', 'AST', 'REB', 'STL', 'BLK', 'FG_PCT', 'FG3_PCT', 
                    'TS_PCT', 'OFF_RATING', 'DEF_RATING', 'NET_RATING', 'PIE']
        
        qualified = self.filter_qualified_players(master)
        qualified = self.calculate_percentiles(qualified, key_stats)
        
        # Save master dataset
        output_file = f"data/processed/master_dataset_{season}.csv"
        qualified.to_csv(output_file, index=False)
        print(f"\nMaster dataset saved to {output_file}")
        print(f"  Total players: {len(qualified)}")
        print(f"  Total columns: {len(qualified.columns)}")
        
        return qualified


def main():
    """
    Example usage
    """
    print("NBA Data Pipeline - Initializing...\n")
    
    # Initialize pipeline
    pipeline = NBADataPipeline(season="2025-26")
    
    # Example 1: Find a specific player
    print("\n" + "="*60)
    print("Example 1: Finding LeBron James")
    print("="*60)
    lebron = pipeline.find_player("LeBron James")
    if lebron:
        print(f"Found: {lebron[0]['full_name']} (ID: {lebron[0]['id']})")
    
    # Example 2: Get league-wide stats
    print("\n" + "="*60)
    print("Example 2: Getting league stats")
    print("="*60)
    league_stats = pipeline.get_league_stats(per_mode='PerGame')
    print(f"\nTop 5 scorers:")
    top_scorers = league_stats.nlargest(5, 'PTS')[['PLAYER_NAME', 'PTS', 'AST', 'REB']]
    try:
        print(top_scorers.to_string(index=False))
    except UnicodeEncodeError:
        # Windows terminal compatibility
        for idx, row in top_scorers.iterrows():
            try:
                print(f"{row['PLAYER_NAME']} - {row['PTS']:.1f} PTS")
            except:
                print(f"[Player name contains special characters] - {row['PTS']:.1f} PTS")
    
    # Example 3: Create master dataset
    print("\n" + "="*60)
    print("Example 3: Creating master dataset")
    print("="*60)
    master = pipeline.create_master_dataset()
    
    # Show sample of master data
    print("\nSample of master dataset:")
    sample_cols = ['PLAYER_NAME', 'PTS', 'AST', 'REB', 'TS_PCT', 
                  'OFF_RATING', 'PIE', 'PTS_PERCENTILE']
    try:
        print(master[sample_cols].head(10).to_string(index=False))
    except UnicodeEncodeError:
        print("[Unicode display error - data saved successfully to CSV]")
    
    print("\n" + "="*60)
    print("Pipeline setup complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Explore the data in data/processed/master_dataset_2025-26.csv")
    print("2. Build your first model using this data")
    print("3. Create visualizations")


if __name__ == "__main__":
    main()
