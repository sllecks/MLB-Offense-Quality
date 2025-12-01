#!/usr/bin/env python3
"""
MLB Opponent-Adjusted Offensive Quality Ranking System

Calculates team offensive performance adjusted for pitcher quality using:
- Game Score = Runs + (0.5 * Hits) + (0.7 * Walks) - (0.25 * Strikeouts)
- Adjusted by opponent's RA9- (pitcher quality metric)

Can be run manually or via cron job throughout the season.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import json
from collections import defaultdict
import sys
import argparse
import math
import os
from pathlib import Path


class MLBOffensiveRanking:
    """Calculate and rank MLB teams by opponent-adjusted offensive quality."""
    
    def __init__(self, season=None, smoothing_factor=0.3):
        self.season = season or datetime.now().year
        self.base_url = "https://statsapi.mlb.com/api/v1"
        self.teams_data = {}
        self.pitcher_stats = {}
        self.park_factors = {}
        
        # Smoothing factor: 0 = no smoothing (original), 1 = maximum smoothing
        # Recommended range: 0.2 - 0.5
        self.smoothing_factor = smoothing_factor
        
        # Linear weights for game score calculation
        self.weights = {
            'runs': 1.0,
            'hits': 0.5,
            'walks': 0.7,
            'strikeouts': -0.25
        }
    
    def fetch_teams(self):
        """Fetch all MLB teams for the current season."""
        url = f"{self.base_url}/teams"
        params = {
            'sportId': 1,  # MLB
            'season': self.season
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            teams = response.json()['teams']
            
            # Filter to only active MLB teams
            self.teams_data = {
                team['id']: {
                    'name': team['name'],
                    'abbreviation': team.get('abbreviation', team['name'][:3].upper()),
                    'division': team.get('division', {}).get('name', 'Unknown')
                }
                for team in teams if team.get('sport', {}).get('id') == 1
            }
            
            print(f"Loaded {len(self.teams_data)} MLB teams for {self.season} season")
            return True
            
        except Exception as e:
            print(f"Error fetching teams: {e}")
            return False
    
    def fetch_schedule(self, team_id, start_date=None, end_date=None):
        """Fetch game schedule for a specific team."""
        if not start_date:
            start_date = f"{self.season}-03-01"
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        url = f"{self.base_url}/schedule"
        params = {
            'sportId': 1,
            'teamId': team_id,
            'startDate': start_date,
            'endDate': end_date,
            'gameType': 'R',  # Regular season only
            'hydrate': 'linescore,team'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json().get('dates', [])
        except Exception as e:
            print(f"Error fetching schedule for team {team_id}: {e}")
            return []
    
    def get_boxscore(self, game_pk):
        """Fetch detailed boxscore for a game."""
        url = f"{self.base_url}/game/{game_pk}/boxscore"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching boxscore for game {game_pk}: {e}")
            return None
    
    def get_pitcher_hand_from_api(self, pitcher_id):
        """Fetch pitcher handedness from person API."""
        url = f"{self.base_url}/people/{pitcher_id}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if 'people' in data and len(data['people']) > 0:
                player = data['people'][0]
                pitch_hand = player.get('pitchHand', {}).get('code', 'Unknown')
                return pitch_hand
            
            return 'Unknown'
        except Exception as e:
            return 'Unknown'
    
    def get_starting_pitcher_hand(self, boxscore, side):
        """
        Extract starting pitcher's throwing hand.
        Returns 'L', 'R', or 'Unknown'
        """
        try:
            # Get the starting pitcher (first pitcher in the list)
            pitchers = boxscore['teams'][side].get('pitchers', [])
            if not pitchers:
                return 'Unknown'
            
            # First pitcher is the starter
            starter_id = pitchers[0]
            
            # Fetch handedness from person API
            return self.get_pitcher_hand_from_api(starter_id)
            
        except Exception as e:
            # If we can't determine handedness, return Unknown
            return 'Unknown'
    
    def calculate_game_score(self, runs, hits, walks, strikeouts):
        """Calculate the raw game score using the formula."""
        score = (
            self.weights['runs'] * runs +
            self.weights['hits'] * hits +
            self.weights['walks'] * walks +
            self.weights['strikeouts'] * strikeouts
        )
        return score
    
    def get_pitcher_ra9_minus(self, pitcher_stats_dict):
        """
        Calculate RA9- for a pitcher or team's pitching staff.
        RA9- = (RA9 / League_RA9) * 100
        Where 100 is average, <100 is better than average, >100 is worse.
        """
        if not pitcher_stats_dict or pitcher_stats_dict.get('innings_pitched', 0) == 0:
            return 100  # Default to league average
        
        runs_allowed = pitcher_stats_dict.get('runs_allowed', 0)
        innings_pitched = pitcher_stats_dict.get('innings_pitched', 0)
        
        if innings_pitched == 0:
            return 100
        
        ra9 = (runs_allowed / innings_pitched) * 9
        
        # Get league average RA9 (will calculate from all teams)
        league_ra9 = pitcher_stats_dict.get('league_avg_ra9', 4.5)  # Default ~4.5
        
        ra9_minus = (ra9 / league_ra9) * 100
        return ra9_minus
    
    def smooth_adjustment_factor(self, ra9_minus):
        """
        Apply smoothing to the RA9- adjustment to create a gradual curve.
        
        This uses a logarithmic smoothing function that:
        - Reduces extreme adjustments (both positive and negative)
        - Creates a smoother transition across pitcher quality levels
        - Maintains directional bias (good pitchers still count more)
        
        Formula:
        - Raw adjustment: ra9_minus / 100
        - Smoothed: 100 + (ra9_minus - 100) * (1 - smoothing_factor)
        - Then convert to adjustment factor
        
        Example with smoothing_factor=0.3:
        - RA9- = 70 (elite): Raw=0.70, Smoothed=0.79 (less dramatic boost)
        - RA9- = 100 (avg): Raw=1.00, Smoothed=1.00 (no change)
        - RA9- = 130 (weak): Raw=1.30, Smoothed=1.21 (less dramatic penalty)
        """
        if self.smoothing_factor == 0:
            # No smoothing, return original
            return ra9_minus / 100.0
        
        # Apply smoothing: compress the distance from 100 (league average)
        deviation = ra9_minus - 100
        smoothed_deviation = deviation * (1 - self.smoothing_factor)
        smoothed_ra9_minus = 100 + smoothed_deviation
        
        # Convert to adjustment factor
        adjustment_factor = smoothed_ra9_minus / 100.0
        
        # Ensure adjustment factor is reasonable (between 0.5 and 1.5)
        # This prevents any single game from being weighted too heavily
        adjustment_factor = max(0.5, min(1.5, adjustment_factor))
        
        return adjustment_factor
    
    def process_team_games(self, team_id):
        """Process all games for a team and calculate offensive metrics."""
        dates = self.fetch_schedule(team_id)
        
        if not dates:
            return []
        
        games_data = []
        
        for date in dates:
            for game in date.get('games', []):
                # Only process completed games
                if game['status']['statusCode'] != 'F':
                    continue
                
                game_pk = game['gamePk']
                boxscore = self.get_boxscore(game_pk)
                
                if not boxscore:
                    continue
                
                # Determine if team was home or away
                home_id = game['teams']['home']['team']['id']
                away_id = game['teams']['away']['team']['id']
                
                is_home = (home_id == team_id)
                team_side = 'home' if is_home else 'away'
                opp_side = 'away' if is_home else 'home'
                
                # Get venue information
                venue = game.get('venue', {})
                venue_id = venue.get('id')
                venue_name = venue.get('name', 'Unknown Venue')
                
                # Get team batting stats
                team_stats = boxscore['teams'][team_side]['teamStats']['batting']
                opp_pitching = boxscore['teams'][opp_side]['teamStats']['pitching']
                
                # Get opponent starting pitcher handedness
                pitcher_hand = self.get_starting_pitcher_hand(boxscore, opp_side)
                
                # Extract relevant stats
                runs = team_stats.get('runs', 0)
                hits = team_stats.get('hits', 0)
                walks = team_stats.get('baseOnBalls', 0)
                strikeouts = team_stats.get('strikeOuts', 0)
                
                # Calculate raw game score
                game_score = self.calculate_game_score(runs, hits, walks, strikeouts)
                
                # Get opponent team ID for pitcher quality adjustment
                opp_id = game['teams'][opp_side]['team']['id']
                
                games_data.append({
                    'game_pk': game_pk,
                    'date': game['gameDate'],
                    'opponent_id': opp_id,
                    'opponent_name': game['teams'][opp_side]['team']['name'],
                    'pitcher_hand': pitcher_hand,  # L, R, or Unknown
                    'is_home': is_home,  # Boolean for home/away splits
                    'venue_id': venue_id,  # For park factor lookup
                    'venue_name': venue_name,  # For display/debugging
                    'runs': runs,
                    'hits': hits,
                    'walks': walks,
                    'strikeouts': strikeouts,
                    'game_score': game_score,
                    'opp_runs_allowed': opp_pitching.get('runs', 0),
                    'opp_innings_pitched': opp_pitching.get('inningsPitched', '0'),
                })
        
        return games_data
    
    def calculate_team_pitching_quality(self):
        """Calculate season-long RA9- for each team's pitching staff."""
        print("\nCalculating team pitching quality (RA9-)...")
        
        pitching_stats = {}
        total_runs = 0
        total_innings = 0
        
        for team_id in self.teams_data.keys():
            url = f"{self.base_url}/teams/{team_id}/stats"
            params = {
                'stats': 'season',
                'group': 'pitching',
                'season': self.season
            }
            
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                stats = response.json()
                
                if stats.get('stats') and len(stats['stats']) > 0:
                    team_stats = stats['stats'][0]['splits']
                    if team_stats:
                        stat = team_stats[0]['stat']
                        runs = stat.get('runs', 0)
                        innings = self.parse_innings(stat.get('inningsPitched', '0'))
                        
                        pitching_stats[team_id] = {
                            'runs_allowed': runs,
                            'innings_pitched': innings
                        }
                        
                        total_runs += runs
                        total_innings += innings
                        
            except Exception as e:
                print(f"Error fetching pitching stats for team {team_id}: {e}")
                pitching_stats[team_id] = {'runs_allowed': 0, 'innings_pitched': 0}
        
        # Calculate league average RA9
        league_ra9 = (total_runs / total_innings * 9) if total_innings > 0 else 4.5
        print(f"League average RA9: {league_ra9:.3f}")
        
        # Calculate RA9- for each team
        for team_id, stats in pitching_stats.items():
            stats['league_avg_ra9'] = league_ra9
            ra9_minus = self.get_pitcher_ra9_minus(stats)
            stats['ra9_minus'] = ra9_minus
            
        self.pitcher_stats = pitching_stats
        return pitching_stats
    
    def parse_innings(self, innings_str):
        """Convert innings string (e.g., '145.1') to float."""
        try:
            if isinstance(innings_str, (int, float)):
                innings_str = str(innings_str)
            
            if '.' in innings_str:
                whole, partial = innings_str.split('.')
                # .1 = 1/3 inning, .2 = 2/3 inning
                return int(whole) + (int(partial) / 3.0)
            return float(innings_str)
        except:
            return 0.0
    
    def calculate_park_factors(self):
        """
        Calculate park factors for all MLB venues dynamically.
        Park Factor = (Runs per game at park / League average runs per game)
        Returns dictionary: {venue_id: park_factor} where 1.0 = neutral
        """
        print("\nCalculating park factors for all venues...")
        
        venue_stats = defaultdict(lambda: {'runs': 0, 'games': 0})
        total_runs = 0
        total_games = 0
        
        # Collect run data for each venue across all teams
        for team_id in self.teams_data.keys():
            dates = self.fetch_schedule(team_id)
            
            if not dates:
                continue
            
            for date in dates:
                for game in date.get('games', []):
                    # Only process completed games
                    if game['status']['statusCode'] != 'F':
                        continue
                    
                    # Get venue info
                    venue = game.get('venue', {})
                    venue_id = venue.get('id')
                    
                    if not venue_id:
                        continue
                    
                    # Get the linescore to sum runs for both teams
                    linescore = game.get('linescore', {})
                    if not linescore:
                        continue
                    
                    home_runs = linescore.get('teams', {}).get('home', {}).get('runs', 0)
                    away_runs = linescore.get('teams', {}).get('away', {}).get('runs', 0)
                    total_game_runs = home_runs + away_runs
                    
                    # Track stats per venue (only count each game once)
                    # We check if this is the home team to avoid double counting
                    home_team_id = game['teams']['home']['team']['id']
                    if home_team_id == team_id:
                        venue_stats[venue_id]['runs'] += total_game_runs
                        venue_stats[venue_id]['games'] += 1
                        total_runs += total_game_runs
                        total_games += 1
        
        # Calculate league average runs per game
        league_avg_runs = total_runs / total_games if total_games > 0 else 4.5
        print(f"League average runs per game: {league_avg_runs:.3f}")
        
        # Calculate park factors
        park_factors = {}
        min_games_threshold = 10  # Require at least 10 games for reliable factor
        
        for venue_id, stats in venue_stats.items():
            if stats['games'] >= min_games_threshold:
                runs_per_game = stats['runs'] / stats['games']
                park_factor = runs_per_game / league_avg_runs
                park_factors[venue_id] = park_factor
            else:
                # Not enough data, default to neutral
                park_factors[venue_id] = 1.0
        
        print(f"Calculated park factors for {len(park_factors)} venues")
        
        # Show top hitter-friendly and pitcher-friendly parks
        sorted_parks = sorted(park_factors.items(), key=lambda x: x[1], reverse=True)
        print("\nTop 5 Hitter-Friendly Parks:")
        for venue_id, factor in sorted_parks[:5]:
            games = venue_stats[venue_id]['games']
            print(f"  Venue {venue_id}: {factor:.3f} ({games} games)")
        
        print("\nTop 5 Pitcher-Friendly Parks:")
        for venue_id, factor in sorted_parks[-5:]:
            games = venue_stats[venue_id]['games']
            print(f"  Venue {venue_id}: {factor:.3f} ({games} games)")
        
        self.park_factors = park_factors
        return park_factors
    
    def calculate_adjusted_offensive_quality(self):
        """Calculate opponent-adjusted offensive quality for all teams."""
        print(f"\nProcessing games for all teams in {self.season}...")
        
        all_team_results = []
        
        for team_id, team_info in self.teams_data.items():
            print(f"Processing {team_info['name']}...")
            
            games = self.process_team_games(team_id)
            
            if not games:
                print(f"  No completed games found for {team_info['name']}")
                continue
            
            # Calculate adjusted scores
            adjusted_scores = []
            adjusted_scores_vs_lhp = []
            adjusted_scores_vs_rhp = []
            adjusted_scores_home = []
            adjusted_scores_away = []
            total_game_score = 0
            
            for game in games:
                game_score = game['game_score']
                total_game_score += game_score
                
                # Get opponent's RA9-
                opp_id = game['opponent_id']
                opp_ra9_minus = self.pitcher_stats.get(opp_id, {}).get('ra9_minus', 100)
                
                # Apply smoothed adjustment factor for opponent quality
                # This creates a gradual sliding scale instead of dramatic swings
                adjustment_factor = self.smooth_adjustment_factor(opp_ra9_minus)
                
                # Get park factor for this game's venue
                venue_id = game.get('venue_id')
                park_factor = self.park_factors.get(venue_id, 1.0) if venue_id else 1.0
                
                # Apply both opponent quality and park factor adjustments
                # Divide by both factors to normalize performance
                combined_adjustment = adjustment_factor * park_factor
                adjusted_score = game_score / combined_adjustment
                
                # For home/away splits, calculate without park factor
                # This shows true home field advantage without park confounding
                adjusted_score_no_park = game_score / adjustment_factor
                
                adjusted_scores.append(adjusted_score)
                
                # Track splits by pitcher handedness (WITH park factors)
                # These splits are about opponent quality, so park normalization applies
                pitcher_hand = game.get('pitcher_hand', 'Unknown')
                if pitcher_hand == 'L':
                    adjusted_scores_vs_lhp.append(adjusted_score)
                elif pitcher_hand == 'R':
                    adjusted_scores_vs_rhp.append(adjusted_score)
                
                # Track splits by home/away (WITHOUT park factors)
                # These splits are about venue advantage, so park adjustment would confound
                is_home = game.get('is_home', False)
                if is_home:
                    adjusted_scores_home.append(adjusted_score_no_park)
                else:
                    adjusted_scores_away.append(adjusted_score_no_park)
            
            # Calculate averages
            games_played = len(games)
            avg_game_score = total_game_score / games_played if games_played > 0 else 0
            avg_adjusted_score = sum(adjusted_scores) / games_played if games_played > 0 else 0
            
            # Calculate split averages - pitcher handedness
            avg_adj_vs_lhp = sum(adjusted_scores_vs_lhp) / len(adjusted_scores_vs_lhp) if adjusted_scores_vs_lhp else 0
            avg_adj_vs_rhp = sum(adjusted_scores_vs_rhp) / len(adjusted_scores_vs_rhp) if adjusted_scores_vs_rhp else 0
            games_vs_lhp = len(adjusted_scores_vs_lhp)
            games_vs_rhp = len(adjusted_scores_vs_rhp)
            
            # Calculate split averages - home/away
            avg_adj_home = sum(adjusted_scores_home) / len(adjusted_scores_home) if adjusted_scores_home else 0
            avg_adj_away = sum(adjusted_scores_away) / len(adjusted_scores_away) if adjusted_scores_away else 0
            games_home = len(adjusted_scores_home)
            games_away = len(adjusted_scores_away)
            
            # Calculate total stats for reference
            total_runs = sum(g['runs'] for g in games)
            total_hits = sum(g['hits'] for g in games)
            total_walks = sum(g['walks'] for g in games)
            total_strikeouts = sum(g['strikeouts'] for g in games)
            
            all_team_results.append({
                'team_id': team_id,
                'team_name': team_info['name'],
                'abbreviation': team_info['abbreviation'],
                'division': team_info['division'],
                'games_played': games_played,
                'avg_game_score': avg_game_score,
                'avg_adjusted_score': avg_adjusted_score,
                'avg_adj_vs_lhp': avg_adj_vs_lhp,
                'avg_adj_vs_rhp': avg_adj_vs_rhp,
                'games_vs_lhp': games_vs_lhp,
                'games_vs_rhp': games_vs_rhp,
                'avg_adj_home': avg_adj_home,
                'avg_adj_away': avg_adj_away,
                'games_home': games_home,
                'games_away': games_away,
                'total_runs': total_runs,
                'avg_runs': total_runs / games_played if games_played > 0 else 0,
                'total_hits': total_hits,
                'total_walks': total_walks,
                'total_strikeouts': total_strikeouts,
            })
        
        return all_team_results
    
    def generate_rankings(self, results):
        """Generate and display rankings."""
        # Sort by adjusted score
        df = pd.DataFrame(results)
        df = df.sort_values('avg_adjusted_score', ascending=False)
        df['rank'] = range(1, len(df) + 1)
        
        # Calculate split rankings - pitcher handedness
        # Sort by vs LHP and assign rank
        df_lhp = df[df['games_vs_lhp'] > 0].copy()
        df_lhp = df_lhp.sort_values('avg_adj_vs_lhp', ascending=False)
        df_lhp['rank_vs_lhp'] = range(1, len(df_lhp) + 1)
        
        # Sort by vs RHP and assign rank
        df_rhp = df[df['games_vs_rhp'] > 0].copy()
        df_rhp = df_rhp.sort_values('avg_adj_vs_rhp', ascending=False)
        df_rhp['rank_vs_rhp'] = range(1, len(df_rhp) + 1)
        
        # Calculate split rankings - home/away
        # Sort by home and assign rank
        df_home = df[df['games_home'] > 0].copy()
        df_home = df_home.sort_values('avg_adj_home', ascending=False)
        df_home['rank_home'] = range(1, len(df_home) + 1)
        
        # Sort by away and assign rank
        df_away = df[df['games_away'] > 0].copy()
        df_away = df_away.sort_values('avg_adj_away', ascending=False)
        df_away['rank_away'] = range(1, len(df_away) + 1)
        
        # Merge the split ranks back into main dataframe
        df = df.merge(
            df_lhp[['team_id', 'rank_vs_lhp']], 
            on='team_id', 
            how='left'
        )
        df = df.merge(
            df_rhp[['team_id', 'rank_vs_rhp']], 
            on='team_id', 
            how='left'
        )
        df = df.merge(
            df_home[['team_id', 'rank_home']], 
            on='team_id', 
            how='left'
        )
        df = df.merge(
            df_away[['team_id', 'rank_away']], 
            on='team_id', 
            how='left'
        )
        
        # Fill NaN ranks with empty string for teams without enough games
        df['rank_vs_lhp'] = df['rank_vs_lhp'].fillna(0).astype(int)
        df['rank_vs_rhp'] = df['rank_vs_rhp'].fillna(0).astype(int)
        df['rank_home'] = df['rank_home'].fillna(0).astype(int)
        df['rank_away'] = df['rank_away'].fillna(0).astype(int)
        
        # Restore original overall rank order
        df = df.sort_values('rank')
        
        # Reorder columns for display
        display_columns = [
            'rank', 'team_name', 'abbreviation', 'games_played',
            'avg_adjusted_score', 
            'rank_vs_lhp', 'avg_adj_vs_lhp', 'games_vs_lhp',
            'rank_vs_rhp', 'avg_adj_vs_rhp', 'games_vs_rhp',
            'rank_home', 'avg_adj_home', 'games_home',
            'rank_away', 'avg_adj_away', 'games_away',
            'avg_game_score', 'avg_runs',
            'total_runs', 'total_hits', 'total_walks', 'total_strikeouts'
        ]
        
        df = df[display_columns]
        
        return df
    
    def save_results(self, df, filename=None):
        """Save results to CSV file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mlb_offensive_rankings_{self.season}_{timestamp}.csv"
        
        # Get the script's directory and create results subdirectory
        script_dir = Path(__file__).parent
        results_dir = script_dir / "results"
        results_dir.mkdir(exist_ok=True)
        
        filepath = results_dir / filename
        df.to_csv(filepath, index=False)
        print(f"\nResults saved to: {filepath}")
        return str(filepath)
    
    def run(self, save_to_file=True, display=True):
        """Main execution method."""
        print(f"="*70)
        print(f"MLB Opponent-Adjusted Offensive Quality Rankings")
        print(f"Season: {self.season}")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"="*70)
        
        # Step 1: Fetch teams
        if not self.fetch_teams():
            print("Failed to fetch teams. Exiting.")
            return None
        
        # Step 2: Calculate park factors
        self.calculate_park_factors()
        
        # Step 3: Calculate pitcher quality for all teams
        self.calculate_team_pitching_quality()
        
        # Step 4: Calculate adjusted offensive quality
        results = self.calculate_adjusted_offensive_quality()
        
        if not results:
            print("\nNo results to display. Exiting.")
            return None
        
        # Step 4: Generate rankings
        df = self.generate_rankings(results)
        
        # Step 5: Display results
        if display:
            print("\n" + "="*70)
            print("FINAL RANKINGS - Opponent-Adjusted Offensive Quality")
            print("="*70)
            
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_rows', None)
            
            print(df.to_string(index=False, float_format=lambda x: f'{x:.2f}'))
            
            print("\n" + "="*70)
            print("METRIC EXPLANATION:")
            print("="*70)
            print("Game Score = Runs + (0.5 × Hits) + (0.7 × Walks) - (0.25 × Strikeouts)")
            print("Adjusted Score = Game Score adjusted by opponent's RA9- and park factors")
            print(f"  - Smoothing factor: {self.smoothing_factor:.2f} (reduces extreme adjustments)")
            print("  - Park factors: Dynamic calculation based on runs scored at each venue")
            print("  - Higher scores indicate better offensive performance")
            print("  - Adjustments account for strength of opposing pitchers AND venue effects")
            print("  - Smoothing creates gradual transitions vs. dramatic swings")
            print("\nSPLITS - Pitcher Handedness:")
            print("  - rank_vs_lhp/rhp: Rank based on performance vs that handedness")
            print("  - avg_adj_vs_lhp/rhp: Adjusted score vs that handedness (WITH park factors)")
            print("  - games_vs_lhp/rhp: Number of games vs that handedness")
            print("\nSPLITS - Home/Away:")
            print("  - rank_home/away: Rank based on performance at home or on the road")
            print("  - avg_adj_home/away: Adjusted score at home or away (NO park factors)")
            print("  - games_home/away: Number of games at home or away")
            print("  - Note: Park factors excluded from home/away to show true venue advantage")
            print("="*70)
        
        # Step 6: Save to file
        if save_to_file:
            self.save_results(df)
        
        return df


def main():
    """Main entry point for script execution."""
    parser = argparse.ArgumentParser(
        description='Calculate MLB Opponent-Adjusted Offensive Quality Rankings'
    )
    parser.add_argument(
        '--season',
        type=int,
        default=None,
        help='MLB season year (default: current year)'
    )
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Do not save results to CSV file'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress display output'
    )
    parser.add_argument(
        '--smoothing',
        type=float,
        default=0.3,
        help='Smoothing factor for opponent adjustment (0.0-1.0, default: 0.3). Higher = more smoothing.'
    )
    
    args = parser.parse_args()
    
    try:
        ranker = MLBOffensiveRanking(season=args.season, smoothing_factor=args.smoothing)
        df = ranker.run(
            save_to_file=not args.no_save,
            display=not args.quiet
        )
        
        if df is not None:
            print("\n✓ Rankings calculation completed successfully!")
            return 0
        else:
            print("\n✗ Rankings calculation failed.")
            return 1
            
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user.")
        return 130
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

