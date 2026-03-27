"""
Supabase Helper Functions
For use in Streamlit app to fetch WAR data
"""

import os
import streamlit as st
from supabase import create_client, Client
import pandas as pd

@st.cache_resource
def get_supabase_client() -> Client:
    """
    Initialize Supabase client
    Uses st.secrets in Streamlit Cloud, env vars locally
    """
    try:
        # Try Streamlit secrets first (for deployed app)
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
    except:
        # Fall back to environment variables
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("Missing Supabase credentials. Add to .streamlit/secrets.toml")
    
    return create_client(url, key)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_latest_ratings() -> pd.DataFrame:
    """
    Fetch the most recent WAR ratings from Supabase
    Returns: DataFrame with all player ratings
    """
    supabase = get_supabase_client()
    
    # Call the SQL function we created
    response = supabase.rpc('get_latest_ratings').execute()
    
    if not response.data:
        return pd.DataFrame()
    
    return pd.DataFrame(response.data)

@st.cache_data(ttl=300)
def get_player_history(player_id: str, days: int = 30) -> pd.DataFrame:
    """
    Get historical WAR ratings for a specific player
    
    Args:
        player_id: The player's ID
        days: Number of days of history to fetch
    
    Returns: DataFrame with player's rating history
    """
    supabase = get_supabase_client()
    
    response = (
        supabase.table('war_ratings')
        .select('*')
        .eq('player_id', player_id)
        .order('calculation_date', desc=True)
        .limit(days)
        .execute()
    )
    
    if not response.data:
        return pd.DataFrame()
    
    return pd.DataFrame(response.data)

@st.cache_data(ttl=300)
def get_team_ratings(team_abbreviation: str) -> pd.DataFrame:
    """
    Get latest ratings for all players on a team
    
    Args:
        team_abbreviation: Team abbreviation (e.g., 'LAL', 'BOS')
    
    Returns: DataFrame with team's player ratings
    """
    supabase = get_supabase_client()
    
    # Get latest calculation date
    latest_date_response = (
        supabase.table('war_ratings')
        .select('calculation_date')
        .order('calculation_date', desc=True)
        .limit(1)
        .execute()
    )
    
    if not latest_date_response.data:
        return pd.DataFrame()
    
    latest_date = latest_date_response.data[0]['calculation_date']
    
    # Get team players from that date
    response = (
        supabase.table('war_ratings')
        .select('*, players(*)')
        .eq('calculation_date', latest_date)
        .eq('players.team_abbreviation', team_abbreviation)
        .order('overall_rating', desc=True)
        .execute()
    )
    
    if not response.data:
        return pd.DataFrame()
    
    return pd.DataFrame(response.data)

def refresh_cache():
    """Clear all cached data to force refresh"""
    st.cache_data.clear()
