"""
NBA Player Ratings Dashboard
Interactive dashboard with manual data refresh, player search, and filtering
"""

import streamlit as st
import pandas as pd
import numpy as np
import subprocess
import os
from datetime import datetime

# Page config
st.set_page_config(
    page_title="NBA Player Ratings Dashboard",
    page_icon="🏀",
    layout="wide"
)

# Title
st.title("🏀 NBA Player Ratings Dashboard")
st.markdown("**WAR-based player ratings • 2025-26 Season**")

# Sidebar - Data Refresh
st.sidebar.header("Data Management")

if st.sidebar.button("🔄 Refresh Data", help="Fetch latest stats from NBA API and recalculate ratings"):
    with st.spinner("Fetching latest NBA data... This may take 2-3 minutes..."):
        try:
            # Run the data pipeline
            result = subprocess.run(
                ["python", "nba_data_pipeline.py"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                st.sidebar.success("✓ Data fetched successfully!")
                
                # Run the model
                with st.spinner("Calculating WAR ratings..."):
                    result = subprocess.run(
                        ["python", "advanced_model.py"],
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    if result.returncode == 0:
                        st.sidebar.success("✓ Ratings updated!")
                        st.rerun()
                    else:
                        st.sidebar.error(f"Model error: {result.stderr}")
            else:
                st.sidebar.error(f"Data fetch error: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            st.sidebar.error("Update timed out. Try again.")
        except Exception as e:
            st.sidebar.error(f"Error: {str(e)}")

# Load data
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("data/processed/player_ratings_2025-26.csv")
        
        # Add last updated timestamp
        if os.path.exists("data/processed/player_ratings_2025-26.csv"):
            last_modified = os.path.getmtime("data/processed/player_ratings_2025-26.csv")
            last_updated = datetime.fromtimestamp(last_modified).strftime("%Y-%m-%d %H:%M")
        else:
            last_updated = "Unknown"
        
        return df, last_updated
    except FileNotFoundError:
        st.error("No ratings data found. Please click 'Refresh Data' to fetch initial data.")
        return None, None

df, last_updated = load_data()

if df is not None:
    st.sidebar.info(f"📅 Last updated: {last_updated}")
    st.sidebar.markdown(f"**{len(df)} players** in database")
    
    # Filters
    st.sidebar.header("Filters")
    
    # Team filter
    teams = ["All Teams"] + sorted(df['TEAM_ABBREVIATION'].unique().tolist())
    selected_team = st.sidebar.selectbox("Team", teams)
    
    # Position filter
    position_col_filter = 'position_detail' if 'position_detail' in df.columns else 'position'
    positions = ["All Positions"] + sorted(df[position_col_filter].dropna().unique().tolist())
    selected_position = st.sidebar.selectbox("Position", positions)
    
    # Tier filter
    tiers = ["All Tiers"] + ["Superstar", "Elite", "All-Star", "Starter", "Rotation", "Deep Bench"]
    selected_tier = st.sidebar.selectbox("Tier", tiers)
    
    # Minutes filter
    min_minutes = st.sidebar.slider("Min MPG", 0, 40, 0)
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_team != "All Teams":
        filtered_df = filtered_df[filtered_df['TEAM_ABBREVIATION'] == selected_team]
    
    if selected_position != "All Positions":
        filtered_df = filtered_df[filtered_df[position_col_filter] == selected_position]
    
    if selected_tier != "All Tiers":
        filtered_df = filtered_df[filtered_df['TIER'] == selected_tier]
    
    filtered_df = filtered_df[filtered_df['MIN'] >= min_minutes]
    
    # Main content
    tab1, tab2, tab3, tab4 = st.tabs(["🏆 Rankings", "🔍 Player Search", "📊 Statistics", "ℹ️ About"])
    
    with tab1:
        st.header("Player Rankings")
        
        # Sort options
        col1, col2 = st.columns([3, 1])
        
        with col1:
            sort_by = st.selectbox(
                "Sort by",
                ["OVERALL_RATING", "OFFENSE_RATING", "DEFENSE_RATING", "TOTAL_WAR", "OFFENSIVE_WAR", "DEFENSIVE_WAR", "PTS", "AST", "REB"]
            )
        
        with col2:
            sort_order = st.radio("Order", ["Descending", "Ascending"], horizontal=True)
        
        # Sort dataframe
        ascending = (sort_order == "Ascending")
        display_df = filtered_df.sort_values(sort_by, ascending=ascending).head(50)
        
        # Display table
        # Use position_detail if available (shows G, G-F, F, F-C, C instead of Guard/Forward/Big)
        position_col = 'position_detail' if 'position_detail' in display_df.columns else 'position'
        
        display_cols = [
            'PLAYER_NAME', 'TEAM_ABBREVIATION', position_col, 
            'OVERALL_RATING', 'OFFENSE_RATING', 'DEFENSE_RATING',
            'TIER', 'MIN', 'PTS', 'AST', 'REB', 'STL', 'BLK'
        ]
        
        st.dataframe(
            display_df[display_cols].reset_index(drop=True).rename(columns={position_col: 'POS'}),
            width='stretch',
            height=600
        )
        
        # Download button
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Current View as CSV",
            data=csv,
            file_name=f"nba_ratings_{selected_team}_{selected_position}.csv",
            mime="text/csv"
        )
    
    with tab2:
        st.header("Player Search & Card Generator")
        
        # Player card generator section
        st.subheader("🎨 Generate Player Card")
        
        # Dropdown to select player
        all_players = sorted(df['PLAYER_NAME'].unique().tolist())
        selected_player_card = st.selectbox(
            "Select a player to generate card:",
            [""] + all_players,
            key="card_generator"
        )
        
        if selected_player_card and st.button("Generate Card", key="gen_card_btn"):
            with st.spinner(f"Generating card for {selected_player_card}..."):
                try:
                    result = subprocess.run(
                        ["python", "create_player_card_futuristic.py", selected_player_card],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        card_path = f"visualizations/{selected_player_card.replace(' ', '_')}_card.png"
                        if os.path.exists(card_path):
                            st.success(f"✓ Card generated!")
                            st.image(card_path, use_column_width=True)
                        else:
                            st.success(f"✓ Card saved to {card_path}")
                    else:
                        st.error(f"Error: {result.stderr}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        st.markdown("---")
        
        # Search box
        st.subheader("🔍 Search Players")
        search_query = st.text_input("Search for a player", placeholder="Enter player name...")
        
        if search_query:
            # Search results
            search_results = df[
                df['PLAYER_NAME'].str.contains(search_query, case=False, na=False)
            ].sort_values('OVERALL_RATING', ascending=False)
            
            if len(search_results) > 0:
                st.success(f"Found {len(search_results)} player(s)")
                
                # Display each player
                for idx, player in search_results.iterrows():
                    # Use position_detail if available
                    pos_display = player.get('position_detail', player.get('position', 'N/A'))
                    
                    with st.expander(f"**{player['PLAYER_NAME']}** - {player['TEAM_ABBREVIATION']} ({pos_display})"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Overall Rating", f"{player['OVERALL_RATING']:.1f}", 
                                     delta=player['TIER'])
                            st.metric("Offensive Rating", f"{player['OFFENSE_RATING']:.1f}")
                            st.metric("Defensive Rating", f"{player['DEFENSE_RATING']:.1f}")
                        
                        with col2:
                            st.metric("Total WAR", f"{player['TOTAL_WAR']:+.1f}")
                            st.metric("Offensive WAR", f"{player['OFFENSIVE_WAR']:+.1f}")
                            st.metric("Defensive WAR", f"{player['DEFENSIVE_WAR']:+.1f}")
                        
                        with col3:
                            st.metric("PPG", f"{player['PTS']:.1f}")
                            st.metric("APG", f"{player['AST']:.1f}")
                            st.metric("RPG", f"{player['REB']:.1f}")
                        
                        # Full stats
                        st.markdown("**Full Statistics:**")
                        stats_cols = st.columns(5)
                        stats_cols[0].write(f"**MIN:** {player['MIN']:.1f}")
                        stats_cols[1].write(f"**STL:** {player['STL']:.1f}")
                        stats_cols[2].write(f"**BLK:** {player['BLK']:.1f}")
                        stats_cols[3].write(f"**TS%:** {player['TS_PCT']:.1%}")
                        stats_cols[4].write(f"**GP:** {int(player['GP'])}")
                        
                        # Rating Explanation
                        st.markdown("---")
                        st.markdown("**📊 Rating Breakdown:**")
                        
                        # Build explanation
                        explanation_parts = []
                        
                        # Offense explanation
                        if player['OFFENSE_RATING'] > 85:
                            explanation_parts.append(f"**Elite offense** ({player['OFFENSE_RATING']:.0f}th percentile): {player['PTS']:.1f} PPG, {player['AST']:.1f} APG, {player['TS_PCT']:.1%} TS%")
                        elif player['OFFENSE_RATING'] > 70:
                            explanation_parts.append(f"**Strong offense** ({player['OFFENSE_RATING']:.0f}th percentile): {player['PTS']:.1f} PPG, {player['AST']:.1f} APG")
                        elif player['OFFENSE_RATING'] > 50:
                            explanation_parts.append(f"**Above average offense** ({player['OFFENSE_RATING']:.0f}th percentile)")
                        else:
                            explanation_parts.append(f"**Limited offense** ({player['OFFENSE_RATING']:.0f}th percentile)")
                        
                        # Defense explanation
                        if player['DEFENSE_RATING'] > 85:
                            explanation_parts.append(f"**Elite defense** ({player['DEFENSE_RATING']:.0f}th percentile): {player['STL']:.1f} STL, {player['BLK']:.1f} BLK, {player['DREB']:.1f} DREB")
                        elif player['DEFENSE_RATING'] > 70:
                            explanation_parts.append(f"**Strong defense** ({player['DEFENSE_RATING']:.0f}th percentile): {player['STL']:.1f} STL, {player['BLK']:.1f} BLK")
                        elif player['DEFENSE_RATING'] > 50:
                            explanation_parts.append(f"**Above average defense** ({player['DEFENSE_RATING']:.0f}th percentile)")
                        else:
                            explanation_parts.append(f"**Limited defense** ({player['DEFENSE_RATING']:.0f}th percentile)")
                        
                        # Minutes/games impact
                        if player['MIN'] >= 30 and player['GP'] >= 60:
                            explanation_parts.append(f"**High volume** ({player['MIN']:.0f} MPG × {int(player['GP'])} GP) boosts overall rating")
                        elif player['MIN'] < 20 or player['GP'] < 40:
                            explanation_parts.append(f"**Limited playing time** ({player['MIN']:.0f} MPG × {int(player['GP'])} GP) reduces overall rating")
                        
                        for part in explanation_parts:
                            st.write(f"• {part}")
                        
                        # Generate player card button
                        if st.button(f"🎨 Generate Player Card", key=f"card_{idx}"):
                            with st.spinner("Generating player card..."):
                                try:
                                    result = subprocess.run(
                                        ["python", "create_player_card_futuristic.py", player['PLAYER_NAME']],
                                        capture_output=True,
                                        text=True,
                                        timeout=30
                                    )
                                    
                                    if result.returncode == 0:
                                        st.success(f"✓ Player card saved to visualizations/{player['PLAYER_NAME'].replace(' ', '_')}_card.png")
                                    else:
                                        st.error(f"Error generating card: {result.stderr}")
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
            else:
                st.warning("No players found matching your search.")
    
    with tab3:
        st.header("League Statistics")
        
        # Summary stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Avg Overall Rating", f"{filtered_df['OVERALL_RATING'].mean():.1f}")
        with col2:
            st.metric("Avg Offensive Rating", f"{filtered_df['OFFENSE_RATING'].mean():.1f}")
        with col3:
            st.metric("Avg Defensive Rating", f"{filtered_df['DEFENSE_RATING'].mean():.1f}")
        with col4:
            st.metric("Avg Total WAR", f"{filtered_df['TOTAL_WAR'].mean():+.1f}")
        
        # Distribution by tier
        st.subheader("Player Distribution by Tier")
        tier_counts = filtered_df['TIER'].value_counts()
        
        # Order tiers from best to worst
        tier_order = ["Superstar", "Elite", "All-Star", "Starter", "Rotation", "Deep Bench"]
        tier_counts = tier_counts.reindex(tier_order, fill_value=0)
        
        st.bar_chart(tier_counts)
        
        # Top performers
        st.subheader("Top 10 Players (Filtered)")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**🎯 Top Scorers**")
            top_scorers = filtered_df.nlargest(10, 'PTS')[['PLAYER_NAME', 'PTS']]
            for idx, row in top_scorers.iterrows():
                st.write(f"{row['PLAYER_NAME']}: {row['PTS']:.1f} PPG")
        
        with col2:
            st.markdown("**🎨 Top Playmakers**")
            top_playmakers = filtered_df.nlargest(10, 'AST')[['PLAYER_NAME', 'AST']]
            for idx, row in top_playmakers.iterrows():
                st.write(f"{row['PLAYER_NAME']}: {row['AST']:.1f} APG")
        
        with col3:
            st.markdown("**🔒 Top Defenders**")
            top_defenders = filtered_df.nlargest(10, 'DEFENSE_RATING')[['PLAYER_NAME', 'DEFENSE_RATING']]
            for idx, row in top_defenders.iterrows():
                st.write(f"{row['PLAYER_NAME']}: {row['DEFENSE_RATING']:.1f}")
    
    with tab4:
        st.header("About This Dashboard")
        
        st.markdown("""
        ## NBA Player Ratings System
        
        Advanced player evaluation using **WAR (Wins Above Replacement)** methodology.
        
        ### How It Works
        
        **Offensive WAR:**
        - Scoring value (volume × efficiency)
        - Playmaking value (assists - turnovers)
        - Spacing value (3PT gravity)
        - Offensive rebounding
        
        **Defensive WAR:**
        - Rim protection (blocks + deterrence)
        - Perimeter defense (steals + pressure)
        - Defensive rebounding
        - Versatility bonus
        - Position-specific weighting (G/G-F/F/F-C/C)
        
        **Team Context:**
        - Players on winning teams receive a boost (0.8x to 1.2x multiplier)
        
        **Total WAR = Offensive WAR + Defensive WAR**
        
        Ratings are converted to percentiles (0-100 scale) for easy interpretation.
        
        ### Rating Tiers
        - 🌟 **Superstar:** 95+ percentile
        - ⭐ **Elite:** 90-94 percentile
        - 🏀 **All-Star:** 85-89 percentile
        - ✅ **Starter:** 67-84 percentile (top 1/3)
        - 🔄 **Rotation:** 30-66 percentile
        - 📊 **Deep Bench:** <30 percentile
        
        ### Key Features
        - **Minutes-weighted:** Stars who play more get higher WAR
        - **Sample size adjusted:** Players with few games are penalized
        - **Position-specific defense:** 5 different defensive formulas (G/G-F/F/F-C/C)
        - **Team success matters:** Winning teams get modest boost
        
        ### Data Source
        - **NBA API** (nba_api Python library)
        - **Current Season:** 2025-26
        - **Update Frequency:** Manual (click "Refresh Data" button)
        - **Minimum:** 10 games, 10 MPG
        
        ---
        
        **Built with:** Python, Streamlit, pandas, nba_api
        """)

else:
    st.info("👈 Click 'Refresh Data' in the sidebar to fetch initial NBA data")
