"""
Advanced NBA Player Rating Model - WAR Based
Uses Wins Above Replacement (WAR) methodology similar to JFresh hockey cards
Converts WAR to percentile ratings (0-100) for user display
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class AdvancedPlayerModel:
    """
    WAR-based player rating model
    Calculates offensive and defensive WAR, then converts to percentile ratings
    """
    
    def __init__(self):
        self.replacement_level_offense = None
        self.replacement_level_defense = None
        self.league_avg_pace = None
        self.league_avg_ts = None
        
    def classify_position(self, player_row):
        """
        Classify player position based on stats (fallback when no manual position)
        Uses 5-position system: Guard, Wing, Forward, Combo Big, Big
        
        Returns: 'Guard', 'Wing', 'Forward', 'Combo Big', or 'Big'
        """
        # If position already classified, use that
        if 'position' in player_row.index and pd.notna(player_row['position']):
            return player_row['position']
        
        # Use stat-based classification
        # NOTE: AST_PCT and REB_PCT are decimals (0.25 = 25%)
        reb_pct = player_row.get('REB_PCT', 0)
        ast_pct = player_row.get('AST_PCT', 0)
        
        # Pure centers: Very high rebounding
        if reb_pct > 0.15:  # 15%+ rebound rate = Centers
            return 'Big'
        
        # Combo bigs: High rebounding but not elite
        if reb_pct > 0.12:  # 12-15% = Stretch bigs
            return 'Combo Big'
        
        # Pure guards: High assist rate + low rebounding
        if ast_pct > 0.20 and reb_pct < 0.08:  # 20%+ assists + low boards = Guards
            return 'Guard'
        
        # Pure guards: Very low rebounding
        if reb_pct < 0.06 and ast_pct > 0.12:  # Low reb + 12%+ assists = Guard
            return 'Guard'
        
        # Wings: Moderate assists with low-medium rebounding
        if ast_pct > 0.18 and reb_pct < 0.10:  # Good assists, not big = Wing
            return 'Wing'
        
        # Bigs: Medium-high rebounding
        if reb_pct > 0.10:  # 10%+ = Forwards/Bigs
            return 'Forward'
        
        # Default: Forward (tweeners, balanced players)
        return 'Forward'
    
    def calculate_replacement_level(self, df):
        """
        Calculate replacement level (45th percentile) for offense and defense
        """
        # Replacement = roughly 45th percentile player
        self.replacement_level_offense = df['PTS'].quantile(0.45)
        self.replacement_level_defense = df['STL'].quantile(0.45) + df['BLK'].quantile(0.45)
        
        # League averages
        self.league_avg_pace = df['PACE'].mean() if 'PACE' in df.columns else 100
        self.league_avg_ts = df['TS_PCT'].mean()
        
        print(f"  Replacement level offense: {self.replacement_level_offense:.1f} PPG")
        print(f"  Replacement level defense: {self.replacement_level_defense:.1f} combined STL+BLK")
        print(f"  League average TS%: {self.league_avg_ts:.1%}")
    
    def calculate_offensive_war(self, df):
        """
        Calculate offensive WAR for each player
        
        Components:
        - Scoring value (volume × efficiency)
        - Playmaking value (assists - turnovers)
        - Spacing value (3PT shooting gravity)
        - Offensive rebounding (second chances)
        """
        df = df.copy()
        
        # A. Scoring Value
        # Efficiency multiplier based on usage
        efficiency_mult = 1 + (df['USG_PCT'] - 20) / 100
        
        # Volume gate: need to be a real scorer (15+ PPG)
        # Stars score 15+ PPG, role players are under that
        volume_penalty = np.minimum(df['PTS'] / 15, 1.0)  # Caps at 1.0 for 15+ PPG
        
        # FG% penalty for bigs - centers should have high FG% since they're near basket
        # Only apply to Bigs and Combo Bigs
        fg_pct_penalty = np.ones(len(df))
        if 'position' in df.columns and 'FG_PCT' in df.columns:
            is_big = df['position'].isin(['Big', 'Combo Big'])
            # Bigs shooting under 50% get penalized (should be 55%+ near basket)
            fg_pct_penalty = np.where(
                is_big & (df['FG_PCT'] < 0.50),
                df['FG_PCT'] / 0.50,  # Linear penalty below 50%
                1.0
            )
        
        # Points created, adjusted for efficiency, volume, and FG% (for bigs)
        ts_bonus = (df['TS_PCT'] - self.league_avg_ts) * 100  # Bonus/penalty for efficiency
        scoring_value = (df['PTS'] * efficiency_mult * volume_penalty * fg_pct_penalty) + ts_bonus
        
        # B. Playmaking Value
        # Assist value varies by role
        assist_value = np.where(
            df['AST_PCT'] > 30, 1.5,  # Primary playmaker
            np.where(df['AST_PCT'] > 20, 1.2, 1.0)  # Secondary/tertiary
        )
        
        # Playmaking volume gate: need at least 4 APG to be considered a real playmaker
        # Increased from 3 to filter out score-first guards
        playmaking_volume_factor = np.minimum(df['AST'] / 4, 1.0)  # Caps at 1.0 for 4+ APG
        
        playmaking_value = (df['AST'] * assist_value * playmaking_volume_factor) - (df['TOV'] * 1.5)
        
        # C. Spacing Value (3PT gravity)
        # High-volume 3PT shooters create spacing even when they don't shoot
        spacing_mult = np.where(
            df['FG3_PCT'] > 0.40, 1.5,
            np.where(df['FG3_PCT'] > 0.36, 1.2, 0.8)
        )
        spacing_value = df['FG3A'] * df['FG3_PCT'] * spacing_mult
        
        # D. Offensive Rebounding (second chance points)
        oreb_value = df['OREB'] * 0.75
        
        # Total offensive impact per game
        offensive_impact = (
            scoring_value +
            playmaking_value +
            spacing_value +
            oreb_value
        )
        
        # Convert to WAR
        # Formula: (Player Impact - Replacement) × (Minutes Factor) / Points Per Win
        minutes_factor = df['MIN'] / 36  # Normalized to 36 MPG
        games_factor = df['GP'] / 82  # Full season = 82 games
        
        points_per_win = 30  # Roughly 30 points of impact = 1 win
        
        offensive_war = (
            (offensive_impact - self.replacement_level_offense) *
            minutes_factor *
            games_factor
        ) / points_per_win
        
        # Floor at -2 WAR (even bad players contribute something)
        offensive_war = offensive_war.clip(lower=-2.0)
        
        return offensive_war
    
    def calculate_defensive_war(self, df):
        """
        Calculate defensive WAR for each player
        
        Components:
        - Rim protection (blocks + deterrence)
        - Perimeter defense (steals + pressure)
        - Defensive rebounding (ending possessions)
        - Versatility bonus
        
        Also calculates defensive impact per 36 for ranking purposes
        """
        df = df.copy()
        df['position'] = df.apply(self.classify_position, axis=1)
        
        # Calculate percentiles for versatility bonus
        stl_pct_rank = df['STL'].rank(pct=True) * 100
        blk_pct_rank = df['BLK'].rank(pct=True) * 100
        
        # A. Rim Protection (mainly for bigs)
        rim_protection = (
            df['BLK'] * 2.0 +  # Direct blocks
            df['BLK'] * 0.8     # Deterrence proxy (shots altered)
        )
        
        # B. Perimeter Defense (mainly for guards/wings)
        perimeter_defense = (
            df['STL'] * 2.0 +   # Reduced from 2.5 - steals were too valuable
            df['STL'] * 0.3     # Reduced deflections proxy from 0.5
        )
        
        # C. Defensive Rebounding (ending possessions)
        defensive_rebounding = df['DREB'] * 0.5
        
        # D. Versatility Bonus (can do multiple things)
        versatility = np.where(
            (stl_pct_rank > 60) & (blk_pct_rank > 60), 1.2, 1.0
        )
        
        # Position-specific weighting (NO team context)
        defensive_impact = []
        
        for idx, row in df.iterrows():
            pos = row['position']
            
            if pos == 'Guard':
                # Pure guards (G): Perimeter defense focus
                # Reduced weighting - steals were inflating guard defense too much
                impact = (
                    perimeter_defense.loc[idx] * 0.55 +  # Reduced from 0.70
                    defensive_rebounding.loc[idx] * 0.35 +  # Increased from 0.25
                    rim_protection.loc[idx] * 0.10  # Increased from 0.05
                ) * versatility[idx]
                
            elif pos == 'Wing':
                # Combo guards/wings (G-F): Balanced perimeter with some versatility
                impact = (
                    perimeter_defense.loc[idx] * 0.60 +
                    rim_protection.loc[idx] * 0.20 +
                    defensive_rebounding.loc[idx] * 0.20
                ) * versatility[idx]
                
            elif pos == 'Forward':
                # Forwards (F): Balanced all-around
                impact = (
                    perimeter_defense.loc[idx] * 0.40 +
                    rim_protection.loc[idx] * 0.35 +
                    defensive_rebounding.loc[idx] * 0.25
                ) * versatility[idx]
                
            elif pos == 'Combo Big':
                # Stretch bigs (F-C): Rim protection with some perimeter
                impact = (
                    rim_protection.loc[idx] * 0.50 +
                    defensive_rebounding.loc[idx] * 0.35 +
                    perimeter_defense.loc[idx] * 0.15
                ) * versatility[idx]
                
            elif pos == 'Big':
                # Pure centers (C): Rim protection and rebounding
                impact = (
                    rim_protection.loc[idx] * 0.55 +
                    defensive_rebounding.loc[idx] * 0.40 +
                    perimeter_defense.loc[idx] * 0.05
                ) * versatility[idx]
                
            else:
                # Default/unknown: balanced
                impact = (
                    perimeter_defense.loc[idx] * 0.40 +
                    rim_protection.loc[idx] * 0.35 +
                    defensive_rebounding.loc[idx] * 0.25
                ) * versatility[idx]
            
            defensive_impact.append(impact)
        
        defensive_impact = pd.Series(defensive_impact, index=df.index)
        
        # Calculate defensive impact per 36 minutes (for ranking defenders)
        # This prevents high-minute players from dominating defensive rankings
        defensive_impact_per36 = defensive_impact / (df['MIN'] / 36)
        
        # Convert to WAR (for overall ratings)
        minutes_factor = df['MIN'] / 36
        games_factor = df['GP'] / 82
        
        stops_per_win = 25  # Roughly 25 defensive stops = 1 win
        
        defensive_war = (
            (defensive_impact - self.replacement_level_defense) *
            minutes_factor *
            games_factor
        ) / stops_per_win
        
        # Floor at -2 WAR
        defensive_war = defensive_war.clip(lower=-2.0)
        
        return defensive_war, defensive_impact_per36
    
    def fit(self, df):
        """
        Train the WAR model (mainly just calculating replacement levels)
        """
        print("Training WAR model...")
        print("="*80)
        
        # Calculate league baselines
        self.calculate_replacement_level(df)
        
        print("\nWAR model ready!")
        print("="*80)
    
    def rate_players(self, df):
        """
        Calculate WAR for all players, then convert to percentile ratings (0-100)
        """
        df = df.copy()
        
        # Add position classification ONLY if not already present from data pipeline
        if 'position' not in df.columns:
            df['position'] = df.apply(self.classify_position, axis=1)
        
        print("\nCalculating WAR for all players...")
        
        # Calculate WAR components
        df['OFFENSIVE_WAR'] = self.calculate_offensive_war(df)
        df['DEFENSIVE_WAR'], df['DEFENSIVE_IMPACT_PER36'] = self.calculate_defensive_war(df)
        df['TOTAL_WAR'] = df['OFFENSIVE_WAR'] + df['DEFENSIVE_WAR']
        
        # Apply diminishing returns for extreme values
        df['TOTAL_WAR'] = df['TOTAL_WAR'].apply(
            lambda x: 15 + (x - 15) * 0.5 if x > 15 else x
        )
        
        # Apply sample size penalty for players with limited games/minutes
        # 45 games threshold to filter small sample flukes like Knueppel
        games_played_factor = np.minimum(df['GP'] / 45, 1.0)  # Full credit at 45+ games
        minutes_factor = np.minimum(df['MIN'] / 28, 1.0)  # Full credit at 28+ MPG (starter minutes)
        sample_size_factor = games_played_factor * minutes_factor
        
        # Apply penalty to total WAR (reduces impact of small sample flukes)
        df['TOTAL_WAR'] = df['TOTAL_WAR'] * sample_size_factor
        
        # Usage-based role player penalty - filters out low-usage efficient guys
        # Stars have 25%+ usage, role players are under 20%
        if 'USG_PCT' in df.columns:
            usage_factor = np.minimum(df['USG_PCT'] / 0.20, 1.0)  # Full credit at 20%+ usage
            df['TOTAL_WAR'] = df['TOTAL_WAR'] * usage_factor
            print("  Applied usage penalty - role players (USG < 20%) penalized")
        
        # Replace team success with NET_RATING (on/off proxy)
        if 'NET_RATING' in df.columns:
            # NET_RATING typically ranges from -15 to +15
            # Convert to multiplier: 0.93x to 1.07x (moderate swing)
            net_rating_factor = 1.0 + (df['NET_RATING'] / 100).clip(-0.07, 0.07)
            df['TOTAL_WAR'] = df['TOTAL_WAR'] * net_rating_factor
            print("  Applied NET_RATING adjustment (0.93x to 1.07x) - on/off proxy")
        
        print(f"  WAR range: {df['TOTAL_WAR'].min():.1f} to {df['TOTAL_WAR'].max():.1f}")
        print(f"  Average WAR: {df['TOTAL_WAR'].mean():.1f}")
        
        # Convert WAR to percentile ratings (0-100 scale)
        df['OFFENSE_RATING'] = (df['OFFENSIVE_WAR'].rank(pct=True) * 100).round(1)
        
        # For defense rating, use impact per 36 (not total WAR)
        # This prevents high-minute players from dominating defensive rankings
        df['DEFENSE_RATING'] = (df['DEFENSIVE_IMPACT_PER36'].rank(pct=True) * 100).round(1)
        
        df['OVERALL_RATING'] = (df['TOTAL_WAR'].rank(pct=True) * 100).round(1)
        
        # Store percentile columns (for compatibility)
        df['OFF_RATING_ADV_PERCENTILE'] = df['OFFENSE_RATING']
        df['DEF_RATING_ADV_PERCENTILE'] = df['DEFENSE_RATING']
        df['OVERALL_PERCENTILE'] = df['OVERALL_RATING']
        
        # Assign tiers based on overall percentile
        def get_tier(percentile):
            if percentile >= 95:
                return "Superstar"
            elif percentile >= 90:
                return "Elite"
            elif percentile >= 85:
                return "All-Star"
            elif percentile >= 67:  # Top 1/3
                return "Starter"
            elif percentile >= 30:
                return "Rotation"
            else:
                return "Deep Bench"
        
        df['TIER'] = df['OVERALL_RATING'].apply(get_tier)
        
        # Maintain compatibility with old column names
        df['MODEL_RATING'] = df['OVERALL_RATING']
        df['RATING_PERCENTILE'] = df['OVERALL_PERCENTILE']
        
        return df


def analyze_war_results(df):
    """
    Print analysis of WAR results
    """
    print("\n" + "="*80)
    print("WAR MODEL RESULTS")
    print("="*80)
    
    print("\nTop 20 Players (by Total WAR):")
    print("-"*80)
    top20 = df.nlargest(20, 'TOTAL_WAR')[
        ['PLAYER_NAME', 'TEAM_ABBREVIATION', 'position', 'TOTAL_WAR', 
         'OFFENSIVE_WAR', 'DEFENSIVE_WAR', 'OVERALL_RATING', 'TIER']
    ]
    for idx, row in top20.iterrows():
        try:
            print(f"{row['PLAYER_NAME']:25s} ({row['TEAM_ABBREVIATION']}) [{row['position']:5s}] - "
                  f"WAR: {row['TOTAL_WAR']:+5.1f} (O: {row['OFFENSIVE_WAR']:+4.1f}, D: {row['DEFENSIVE_WAR']:+4.1f}) | "
                  f"Rating: {row['OVERALL_RATING']:5.1f} | {row['TIER']}")
        except UnicodeEncodeError:
            # Windows terminal fallback - show stats without special characters in name
            print(f"[Player] ({row['TEAM_ABBREVIATION']}) [{row['position']:5s}] - "
                  f"WAR: {row['TOTAL_WAR']:+5.1f} (O: {row['OFFENSIVE_WAR']:+4.1f}, D: {row['DEFENSIVE_WAR']:+4.1f}) | "
                  f"Rating: {row['OVERALL_RATING']:5.1f} | {row['TIER']}")
    
    print("\n" + "-"*80)
    print("Best Offensive Players (by Offensive WAR):")
    print("-"*80)
    top_off = df.nlargest(10, 'OFFENSIVE_WAR')[
        ['PLAYER_NAME', 'OFFENSIVE_WAR', 'PTS', 'AST', 'TS_PCT']
    ]
    for idx, row in top_off.iterrows():
        try:
            print(f"{row['PLAYER_NAME']:25s} | Off WAR: {row['OFFENSIVE_WAR']:+5.1f} | "
                  f"{row['PTS']:.1f} PPG, {row['AST']:.1f} AST, {row['TS_PCT']:.1%} TS")
        except UnicodeEncodeError:
            print(f"[Player] | Off WAR: {row['OFFENSIVE_WAR']:+5.1f} | "
                  f"{row['PTS']:.1f} PPG, {row['AST']:.1f} AST, {row['TS_PCT']:.1%} TS")
    
    print("\n" + "-"*80)
    print("Best Defensive Players (by Defensive Impact per 36):")
    print("-"*80)
    top_def = df.nlargest(10, 'DEFENSIVE_IMPACT_PER36')[
        ['PLAYER_NAME', 'DEFENSIVE_IMPACT_PER36', 'MIN', 'STL', 'BLK', 'DREB']
    ]
    for idx, row in top_def.iterrows():
        try:
            print(f"{row['PLAYER_NAME']:25s} | Def Impact/36: {row['DEFENSIVE_IMPACT_PER36']:5.1f} | "
                  f"{row['MIN']:.1f} MPG | {row['STL']:.1f} STL, {row['BLK']:.1f} BLK, {row['DREB']:.1f} DREB")
        except UnicodeEncodeError:
            print(f"[Player] | Def Impact/36: {row['DEFENSIVE_IMPACT_PER36']:5.1f} | "
                  f"{row['MIN']:.1f} MPG | {row['STL']:.1f} STL, {row['BLK']:.1f} BLK, {row['DREB']:.1f} DREB")
    
    print("\n" + "-"*80)
    print("Tier Distribution:")
    print("-"*80)
    tier_counts = df['TIER'].value_counts()
    for tier in ["Superstar", "Elite", "All-Star", "Starter", "Rotation", "Deep Bench"]:
        count = tier_counts.get(tier, 0)
        pct = count / len(df) * 100
        print(f"  {tier:15s}: {count:3d} players ({pct:4.1f}%)")


def main():
    """
    Train WAR model and generate ratings
    """
    print("\n" + "="*80)
    print("NBA PLAYER WAR MODEL")
    print("="*80 + "\n")
    
    # Load data
    print("Loading data...")
    try:
        df = pd.read_csv("data/processed/master_dataset_2025-26.csv")
        print(f"Loaded {len(df)} players (2025-26)\n")
    except FileNotFoundError:
        try:
            df = pd.read_csv("data/processed/master_dataset_2024-25.csv")
            print(f"Loaded {len(df)} players (2024-25)\n")
        except FileNotFoundError:
            print("ERROR: Master dataset not found!")
            print("Please run nba_data_pipeline.py first to fetch data.")
            return
    
    # Train WAR model
    war_model = AdvancedPlayerModel()
    war_model.fit(df)
    
    # Rate all players
    print("\nRating all players...")
    df_rated = war_model.rate_players(df)
    
    # Analyze results
    analyze_war_results(df_rated)
    
    # Save results
    output_file = "data/processed/player_ratings_war_2025-26.csv"
    df_rated.to_csv(output_file, index=False)
    print(f"\nWAR ratings saved to {output_file}")
    
    # Also save as the default ratings file (for player cards)
    output_file_default = "data/processed/player_ratings_2025-26.csv"
    df_rated.to_csv(output_file_default, index=False)
    print(f"Saved as default ratings file: {output_file_default}")
    
    print("\n" + "="*80)
    print("WAR model complete!")
    print("  * Minutes naturally weighted (stars play more = higher WAR)")
    print("  * Cumulative impact (not per-minute inflation)")
    print("  * Converted to 0-100 percentile ratings for display")
    print("\nNext: Run validate_model.py to check accuracy!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
