"""
Futuristic Player Card Generator - Cyberpunk/Sci-Fi Style
Creates modern, dark-mode player cards with glowing neon effects
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle, FancyBboxPatch, Wedge
from matplotlib.path import Path
import matplotlib.patheffects as path_effects
import numpy as np
import sys


class FuturisticPlayerCard:
    """
    Generate futuristic player cards with cyberpunk aesthetics
    """
    
    def __init__(self, ratings_file="data/processed/player_ratings_2025-26.csv"):
        """Load player ratings data"""
        try:
            self.df = pd.read_csv(ratings_file)
        except FileNotFoundError:
            # Try alternate location
            self.df = pd.read_csv("data/processed/player_ratings_2024-25.csv")
        
    def find_player(self, player_name):
        """Find player in dataset"""
        matches = self.df[
            self.df['PLAYER_NAME'].str.contains(player_name, case=False, na=False)
        ]
        
        if len(matches) == 0:
            print(f"No player found matching '{player_name}'")
            return None
        elif len(matches) > 1:
            print(f"Multiple players found:")
            for idx, row in matches.iterrows():
                print(f"  - {row['PLAYER_NAME']} ({row['TEAM_ABBREVIATION']})")
            return None
        
        return matches.iloc[0]
    
    def create_card(self, player_name, output_file=None):
        """
        Create a futuristic player card
        
        Args:
            player_name: Name of player
            output_file: Where to save (default: player_name_futuristic.png)
        """
        player = self.find_player(player_name)
        if player is None:
            return
        
        if output_file is None:
            safe_name = player['PLAYER_NAME'].replace(' ', '_').lower()
            output_file = f"visualizations/{safe_name}_futuristic.png"
        
        # Futuristic color scheme - Dark mode with neon accents
        bg_color = '#0A0E27'           # Deep space blue-black
        card_bg = '#121B3A'            # Slightly lighter panel
        primary_text = '#E0E6F0'       # Cool white
        secondary_text = '#8B96B8'     # Muted blue-gray
        
        # Neon accent colors
        neon_cyan = '#00F0FF'          # Electric cyan
        neon_pink = '#FF006E'          # Hot pink
        neon_purple = '#9D4EDD'        # Purple
        neon_green = '#39FF14'         # Matrix green
        
        # Tier colors (neon variants) - percentile based
        tier_colors = {
            'Superstar': '#39FF14',    # Neon green (95+)
            'Elite': '#00F0FF',        # Cyan (85-94)
            'All-Star': '#9D4EDD',     # Purple (70-84)
            'Starter': '#FFB627',      # Gold (50-69)
            'Rotation': '#FF6B35',     # Orange (30-49)
            'Deep Bench': '#8B96B8'    # Gray (below 30)
        }
        
        # Create figure with dark background
        fig = plt.figure(figsize=(10, 13), facecolor=bg_color)
        
        # Main layout
        gs = fig.add_gridspec(5, 1, height_ratios=[1.2, 0.8, 2.2, 3, 1.5], 
                             hspace=0.35, top=0.96, bottom=0.04, 
                             left=0.08, right=0.92)
        
        # ==================
        # 1. HEADER WITH GLOWING TITLE
        # ==================
        ax_header = fig.add_subplot(gs[0])
        ax_header.set_xlim(0, 1)
        ax_header.set_ylim(0, 1)
        ax_header.axis('off')
        ax_header.set_facecolor(bg_color)
        
        # Player name with glow effect
        player_text = ax_header.text(0.05, 0.6, player['PLAYER_NAME'].upper(), 
                      fontsize=36, fontweight='bold', color=primary_text,
                      family='monospace')
        
        # Add glow effect
        player_text.set_path_effects([
            path_effects.withStroke(linewidth=8, foreground=neon_cyan, alpha=0.3),
            path_effects.Normal()
        ])
        
        # Subtitle with team
        season_text = ax_header.text(0.05, 0.25, 
                      f"[{player['TEAM_ABBREVIATION']}] // 2025-26 SEASON", 
                      fontsize=11, color=secondary_text, family='monospace',
                      style='italic')
        
        # Futuristic separator line
        ax_header.plot([0.05, 0.95], [0.05, 0.05], color=neon_cyan, 
                      linewidth=1, alpha=0.5)
        
        # ==================
        # 2. RATING HEXAGON (TOP RIGHT)
        # ==================
        ax_rating = fig.add_subplot(gs[1])
        ax_rating.set_xlim(0, 1)
        ax_rating.set_ylim(0, 1)
        ax_rating.axis('off')
        ax_rating.set_facecolor(bg_color)
        
        rating_value = round(player['MODEL_RATING'], 1)
        tier = player['TIER']
        tier_color = tier_colors.get(tier, secondary_text)
        
        # Draw hexagonal rating badge
        hex_center = (0.5, 0.5)
        hex_radius = 0.35
        
        # Create hexagon points
        angles = np.linspace(0, 2*np.pi, 7)
        hex_x = hex_center[0] + hex_radius * np.cos(angles)
        hex_y = hex_center[1] + hex_radius * np.sin(angles)
        
        # Outer glow hexagon
        hex_outer = mpatches.Polygon(list(zip(hex_x * 1.1, hex_y * 1.1)),
                                    facecolor=tier_color, alpha=0.15,
                                    edgecolor='none')
        ax_rating.add_patch(hex_outer)
        
        # Main hexagon
        hex_main = mpatches.Polygon(list(zip(hex_x, hex_y)),
                                   facecolor=card_bg, 
                                   edgecolor=tier_color, linewidth=3)
        ax_rating.add_patch(hex_main)
        
        # Rating number
        rating_txt = ax_rating.text(hex_center[0], hex_center[1] + 0.08, 
                      f"{int(round(rating_value))}", 
                      fontsize=28, fontweight='bold', color=tier_color,
                      ha='center', va='center', family='monospace')
        rating_txt.set_path_effects([
            path_effects.withStroke(linewidth=3, foreground=tier_color, alpha=0.3)
        ])
        
        # Tier label
        ax_rating.text(hex_center[0], hex_center[1] - 0.15, 
                      tier.upper(), 
                      fontsize=9, color=secondary_text,
                      ha='center', va='center', family='monospace',
                      weight='bold')
        
        # Corner brackets (cyberpunk style)
        bracket_color = neon_cyan
        bracket_size = 0.08
        ax_rating.plot([0, bracket_size], [0, 0], color=bracket_color, linewidth=2, alpha=0.6)
        ax_rating.plot([0, 0], [0, bracket_size], color=bracket_color, linewidth=2, alpha=0.6)
        ax_rating.plot([1, 1-bracket_size], [0, 0], color=bracket_color, linewidth=2, alpha=0.6)
        ax_rating.plot([1, 1], [0, bracket_size], color=bracket_color, linewidth=2, alpha=0.6)
        
        # ==================
        # 3. STAT BREAKDOWN WITH CONTRIBUTORS
        # ==================
        ax_breakdown = fig.add_subplot(gs[2])
        ax_breakdown.set_xlim(0, 1)
        ax_breakdown.set_ylim(0, 1)
        ax_breakdown.axis('off')
        ax_breakdown.set_facecolor(bg_color)
        
        # Section title
        title = ax_breakdown.text(0.05, 0.95, "// RATING BREAKDOWN", 
                  fontsize=12, color=neon_cyan, family='monospace',
                  weight='bold')
        
        # Rating components with their contributors
        components = [
            {
                'name': 'SCORING',
                'percentile': player.get('PTS_PERCENTILE', 50),
                'color': neon_pink
            },
            {
                'name': 'PLAYMAKING', 
                'percentile': player.get('AST_PERCENTILE', 50),
                'color': neon_purple
            },
            {
                'name': 'REBOUNDING',
                'percentile': player.get('REB_PERCENTILE', 50),
                'color': neon_cyan
            },
            {
                'name': 'EFFICIENCY',
                'percentile': player.get('TS_PCT_PERCENTILE', 50),
                'color': neon_green
            },
            {
                'name': 'DEFENSE',
                'percentile': player.get('DEF_RATING_PERCENTILE', 50),
                'color': '#FFB627'
            },
        ]
        
        y_pos = 0.85
        spacing = 0.18
        
        for comp in components:
            # Stat name
            ax_breakdown.text(0.08, y_pos, comp['name'], 
                            fontsize=11, color=primary_text,
                            family='monospace', weight='bold')
            
            # Progress bar background
            bar_start = 0.30
            bar_width = 0.60
            bar_height = 0.045
            
            # Background bar
            bg_rect = Rectangle((bar_start, y_pos - bar_height/2), bar_width, bar_height,
                              facecolor=card_bg, edgecolor=secondary_text, 
                              linewidth=0.5, alpha=0.3)
            ax_breakdown.add_patch(bg_rect)
            
            # Filled bar (with gradient effect via alpha)
            fill_width = (comp['percentile'] / 100) * bar_width
            fill_rect = Rectangle((bar_start, y_pos - bar_height/2), fill_width, bar_height,
                                 facecolor=comp['color'], edgecolor='none', alpha=0.8)
            ax_breakdown.add_patch(fill_rect)
            
            # Glow effect
            glow_rect = Rectangle((bar_start, y_pos - bar_height/2), fill_width, bar_height,
                                 facecolor=comp['color'], edgecolor='none', alpha=0.2)
            glow_rect.set_transform(ax_breakdown.transData)
            ax_breakdown.add_patch(glow_rect)
            
            # Percentile value
            ax_breakdown.text(bar_start + bar_width + 0.02, y_pos, 
                            f"{comp['percentile']:.0f}", 
                            fontsize=11, color=comp['color'],
                            va='center', family='monospace', weight='bold')
            
            y_pos -= spacing
        
        # ==================
        # 4. RADAR CHART (FUTURISTIC STYLE)
        # ==================
        ax_radar = fig.add_subplot(gs[3], projection='polar')
        ax_radar.set_facecolor(bg_color)
        
        # Radar data
        radar_stats = [
            ('SCORE', player.get('PTS_PERCENTILE', 50)),
            ('SHOOT', player.get('TS_PCT_PERCENTILE', 50)),
            ('PASS', player.get('AST_PERCENTILE', 50)),
            ('BOARD', player.get('REB_PERCENTILE', 50)),
            ('DEFEND', player.get('DEF_RATING_PERCENTILE', 50)),
            ('IMPACT', player.get('PIE_PERCENTILE', 50)),
        ]
        
        categories = [s[0] for s in radar_stats]
        values = [s[1] for s in radar_stats]
        
        # Complete the loop
        values += values[:1]
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]
        
        # Plot player data with glow
        ax_radar.plot(angles, values, 'o-', linewidth=3, 
                     color=neon_cyan, markersize=8, markeredgewidth=2,
                     markeredgecolor=bg_color, label='PLAYER',
                     path_effects=[path_effects.withStroke(linewidth=6, 
                                   foreground=neon_cyan, alpha=0.3)])
        ax_radar.fill(angles, values, alpha=0.25, color=neon_cyan)
        
        # League average reference
        avg_values = [50] * len(angles)
        ax_radar.plot(angles, avg_values, '--', linewidth=2, 
                     color=secondary_text, alpha=0.5, label='LEAGUE AVG')
        
        # Styling
        ax_radar.set_theta_offset(np.pi / 2)
        ax_radar.set_theta_direction(-1)
        ax_radar.set_ylim(0, 100)
        ax_radar.set_xticks(angles[:-1])
        ax_radar.set_xticklabels(categories, fontsize=11, color=primary_text,
                                family='monospace', weight='bold')
        
        # Grid styling
        ax_radar.set_yticks([25, 50, 75])
        ax_radar.set_yticklabels(['25', '50', '75'], fontsize=8, 
                                color=secondary_text, family='monospace')
        ax_radar.grid(color=secondary_text, linewidth=0.5, alpha=0.3, linestyle=':')
        ax_radar.spines['polar'].set_color(neon_cyan)
        ax_radar.spines['polar'].set_linewidth(2)
        ax_radar.spines['polar'].set_alpha(0.5)
        
        # Legend
        legend = ax_radar.legend(loc='upper right', bbox_to_anchor=(1.25, 1.15), 
                               fontsize=9, framealpha=0.9, facecolor=card_bg,
                               edgecolor=neon_cyan)
        legend.get_frame().set_linewidth(1.5)
        for text in legend.get_texts():
            text.set_color(primary_text)
            text.set_family('monospace')
        
        # ==================
        # 5. BOX SCORE MATRIX
        # ==================
        ax_box = fig.add_subplot(gs[4])
        ax_box.set_xlim(0, 1)
        ax_box.set_ylim(0, 1)
        ax_box.axis('off')
        ax_box.set_facecolor(bg_color)
        
        # Section title
        ax_box.text(0.05, 0.85, "// STATISTICS MATRIX", 
                   fontsize=11, color=neon_cyan, family='monospace', weight='bold')
        
        # Stats grid
        stats_grid = [
            [('GP', int(player['GP'])), ('MIN', f"{int(round(player['MIN']))}"), 
             ('PTS', f"{int(round(player['PTS']))}"), ('REB', f"{int(round(player['REB']))}")],
            [('AST', f"{int(round(player['AST']))}"), ('STL', f"{int(round(player['STL']))}"),
             ('BLK', f"{int(round(player['BLK']))}"), ('FG%', f"{int(round(player['FG_PCT']*100))}")],
        ]
        
        y_start = 0.58
        x_positions = [0.08, 0.30, 0.52, 0.74]
        row_height = 0.28
        
        for row_idx, row in enumerate(stats_grid):
            y_pos = y_start - (row_idx * row_height)
            
            for col_idx, (label, value) in enumerate(row):
                x_pos = x_positions[col_idx]
                
                # Stat label
                ax_box.text(x_pos, y_pos, label, 
                           fontsize=8, color=secondary_text,
                           family='monospace')
                
                # Stat value (larger, colored)
                val_text = ax_box.text(x_pos, y_pos - 0.12, str(value),
                           fontsize=13, color=neon_green,
                           family='monospace', weight='bold')
                val_text.set_path_effects([
                    path_effects.withStroke(linewidth=2, foreground=neon_green, alpha=0.2)
                ])
        
        # Bottom border
        ax_box.plot([0.05, 0.95], [0.05, 0.05], color=neon_cyan, 
                   linewidth=1, alpha=0.5)
        
        # Save with tight layout
        plt.savefig(output_file, dpi=300, bbox_inches='tight', 
                   facecolor=bg_color, edgecolor='none')
        print(f"Futuristic player card saved to {output_file}")
        plt.close()


def main():
    """
    Generate futuristic player card from command line
    
    Usage: python create_player_card_futuristic.py "Player Name"
    """
    if len(sys.argv) < 2:
        print("Usage: python create_player_card_futuristic.py \"Player Name\"")
        print("Example: python create_player_card_futuristic.py \"LeBron James\"")
        return
    
    player_name = sys.argv[1]
    
    # Create output directory
    import os
    os.makedirs("visualizations", exist_ok=True)
    
    # Generate card
    generator = FuturisticPlayerCard()
    generator.create_card(player_name)


if __name__ == "__main__":
    main()
