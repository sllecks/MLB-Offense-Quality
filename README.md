# MLB Opponent-Adjusted Offensive Rankings

A Python-based ranking system that evaluates MLB team offensive performance while accounting for opponent pitcher quality and park factors. This provides a more accurate assessment of offensive strength than traditional counting stats.

## Overview

Traditional offensive statistics can be misleading when teams face vastly different levels of pitching competition or play in ballparks with extreme characteristics. This system addresses both issues by:

1. **Adjusting for opponent pitcher quality** using RA9- (Runs Allowed per 9 innings, normalized to 100)
2. **Adjusting for park factors** calculated dynamically from current season data
3. **Providing pitcher handedness and home/away splits** for matchup analysis

## The Formulas

### 1. Game Score Calculation

Each offensive performance is quantified using a linear weights formula:

```
Game Score = Runs + (0.5 × Hits) + (0.7 × Walks) - (0.25 × Strikeouts)
```

**Component Weights and Rationale:**

| Component | Weight | Rationale |
|-----------|--------|-----------|
| Runs | 1.0 | The ultimate goal of offense; given full weight |
| Hits | 0.5 | Baserunners that create scoring opportunities |
| Walks | 0.7 | High-value plate appearances showing discipline; weighted higher than hits based on sabermetric research |
| Strikeouts | -0.25 | Unproductive outs that end rallies; penalized but not overly punitive |

These weights are based on linear weights analysis from modern baseball analytics, reflecting the run expectancy value of each outcome.

### 2. Adjustment Factor (Opponent Quality)

The adjustment factor normalizes performance based on opponent pitcher strength:

```
deviation = RA9- - 100
smoothed_deviation = deviation × (1 - smoothing_factor)
smoothed_RA9- = 100 + smoothed_deviation
adjustment_factor = smoothed_RA9- / 100
adjustment_factor = max(0.5, min(1.5, adjustment_factor))
```

**Simplified:**
```
adjustment_factor = [100 + (RA9- - 100) × (1 - α)] / 100
```
where α = smoothing factor (default: 0.3)

**Rationale:**
- **RA9- = 100**: League average (no adjustment)
- **RA9- < 100**: Elite pitching (adjustment < 1.0, boosts offensive score)
- **RA9- > 100**: Below-average pitching (adjustment > 1.0, reduces offensive score)
- **Smoothing (α = 0.3)**: Prevents extreme single-game variance while maintaining directional accuracy
- **Bounds [0.5, 1.5]**: Caps maximum adjustment to prevent outliers from dominating the metric

**Example:**
- Against elite pitcher (RA9- = 70): adjustment_factor = 0.79, so a game score of 10 becomes 10/0.79 = 12.66
- Against weak pitcher (RA9- = 130): adjustment_factor = 1.21, so a game score of 10 becomes 10/1.21 = 8.26

### 3. Park Factor Calculation

Park factors are calculated dynamically from current season data:

```
Park Factor = (Total runs scored at venue / Games at venue) / League average runs per game
```

**Rationale:**
- Calculated fresh each season rather than using historical data
- Requires minimum 10 games for reliability (defaults to 1.0 otherwise)
- Accounts for current conditions: recent renovations, altitude effects, weather patterns
- **Park Factor = 1.0**: Neutral park
- **Park Factor > 1.0**: Hitter-friendly (e.g., Coors Field ~1.15)
- **Park Factor < 1.0**: Pitcher-friendly (e.g., Oracle Park ~0.92)

### 4. Combined Adjusted Score

The final adjusted score combines both adjustments:

```
Adjusted Score = Game Score / (adjustment_factor × park_factor)
```

**Rationale:**
- Division normalizes inflated scores (easier opponents/parks) and boosts suppressed scores (tougher opponents/parks)
- Multiplicative combination accounts for independent effects of opponent quality and venue
- Final score represents what the offensive output "would have been" in neutral conditions against average pitching

### 5. Average Adjusted Score

The primary ranking metric is the mean across all games:

```
Average Adjusted Score = Σ(Adjusted Scores) / Games Played
```

This provides a season-long evaluation of offensive quality on a level playing field.

## 2025 Season Rankings (as of Dec 1, 2025)

Complete rankings showing overall performance and pitcher handedness splits:

| Rank | Team | GP | Adj Score | vs LHP Rank | vs LHP Score | vs RHP Rank | vs RHP Score |
|------|------|----|-----------:|------------:|-------------:|------------:|-------------:|
| 1 | Milwaukee Brewers | 162 | 10.08 | 3 | 10.20 | 1 | 10.03 |
| 2 | New York Yankees | 161 | 10.00 | 1 | 10.52 | 4 | 9.86 |
| 3 | Seattle Mariners | 162 | 9.61 | 10 | 8.83 | 2 | 9.93 |
| 4 | Toronto Blue Jays | 161 | 9.60 | 2 | 10.32 | 7 | 9.36 |
| 5 | Chicago Cubs | 162 | 9.58 | 14 | 8.67 | 3 | 9.90 |
| 6 | Boston Red Sox | 163 | 9.27 | 4 | 9.72 | 12 | 9.09 |
| 7 | San Diego Padres | 162 | 9.24 | 8 | 8.87 | 6 | 9.40 |
| 8 | Kansas City Royals | 162 | 9.14 | 22 | 7.93 | 5 | 9.45 |
| 9 | Los Angeles Dodgers | 162 | 9.13 | 5 | 9.03 | 9 | 9.18 |
| 10 | Texas Rangers | 162 | 9.07 | 7 | 8.92 | 11 | 9.13 |
| 11 | Miami Marlins | 162 | 8.99 | 9 | 8.84 | 13 | 9.05 |
| 12 | Philadelphia Phillies | 162 | 8.97 | 20 | 8.26 | 8 | 9.28 |
| 13 | New York Mets | 162 | 8.96 | 11 | 8.78 | 14 | 9.04 |
| 14 | Atlanta Braves | 163 | 8.91 | 12 | 8.77 | 16 | 8.96 |
| 15 | Arizona Diamondbacks | 163 | 8.88 | 13 | 8.74 | 17 | 8.94 |
| 16 | St. Louis Cardinals | 162 | 8.80 | 16 | 8.56 | 18 | 8.89 |
| 17 | Houston Astros | 161 | 8.77 | 15 | 8.57 | 20 | 8.82 |
| 18 | Cincinnati Reds | 164 | 8.76 | 17 | 8.54 | 19 | 8.85 |
| 19 | Tampa Bay Rays | 162 | 8.63 | 26 | 7.40 | 10 | 9.14 |
| 20 | Detroit Tigers | 162 | 8.60 | 18 | 8.51 | 21 | 8.63 |
| 21 | Athletics | 162 | 8.44 | 6 | 8.99 | 25 | 8.26 |
| 22 | San Francisco Giants | 161 | 8.43 | 28 | 7.01 | 15 | 8.98 |
| 23 | Cleveland Guardians | 163 | 8.20 | 23 | 7.90 | 24 | 8.32 |
| 24 | Chicago White Sox | 159 | 8.16 | 24 | 7.88 | 26 | 8.25 |
| 25 | Pittsburgh Pirates | 162 | 8.13 | 19 | 8.28 | 28 | 8.09 |
| 26 | Minnesota Twins | 161 | 8.13 | 27 | 7.20 | 23 | 8.39 |
| 27 | Baltimore Orioles | 162 | 7.96 | 25 | 7.51 | 27 | 8.14 |
| 28 | Washington Nationals | 162 | 7.78 | 29 | 6.30 | 22 | 8.41 |
| 29 | Los Angeles Angels | 162 | 7.36 | 21 | 7.97 | 29 | 7.23 |
| 30 | Colorado Rockies | 162 | 6.04 | 30 | 6.19 | 30 | 5.98 |

**Key Insights:**
- The **Yankees** dominate vs LHP (10.52) but are more vulnerable vs RHP
- The **Royals** show a massive platoon split: 22nd vs LHP, 5th vs RHP
- The **Rays** similarly excel vs RHP (10th) despite struggling vs LHP (26th)
- The **Rockies** rank last even after park adjustment, highlighting systemic offensive issues

## Installation

### Prerequisites
- Python 3.7+
- Internet connection (for MLB Stats API access)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/baseballSOS.git
cd baseballSOS
```

2. Create and activate a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run analysis for the current season:
```bash
python mlb_offense_quality.py
```

### Command Line Options

```bash
# Specify a different season
python mlb_offense_quality.py --season 2024

# Adjust smoothing factor (0.0 = no smoothing, 1.0 = maximum)
python mlb_offense_quality.py --smoothing 0.3  # Default
python mlb_offense_quality.py --smoothing 0.0  # More dramatic adjustments
python mlb_offense_quality.py --smoothing 0.5  # Gentler adjustments

# Skip CSV export
python mlb_offense_quality.py --no-save

# Quiet mode (suppress console output)
python mlb_offense_quality.py --quiet

# Combine options
python mlb_offense_quality.py --season 2024 --smoothing 0.4
```

### Output

The script generates:

1. **Console output**: Formatted rankings table with key metrics
2. **CSV file**: Timestamped file in `results/` directory with format:
   ```
   mlb_offensive_rankings_YYYY_YYYYMMDD_HHMMSS.csv
   ```

**CSV Columns:**
- `rank`: Overall ranking by adjusted score
- `team_name`, `abbreviation`: Team identifiers
- `games_played`: Games included in analysis
- `avg_adjusted_score`: Primary metric (park + opponent adjusted)
- `rank_vs_lhp`, `avg_adj_vs_lhp`, `games_vs_lhp`: Performance vs left-handed starters
- `rank_vs_rhp`, `avg_adj_vs_rhp`, `games_vs_rhp`: Performance vs right-handed starters
- `rank_home`, `avg_adj_home`, `games_home`: Home performance (opponent-adjusted only)
- `rank_away`, `avg_adj_away`, `games_away`: Road performance (opponent-adjusted only)
- `avg_game_score`: Unadjusted average
- `avg_runs`, `total_runs`: Raw run scoring
- `total_hits`, `total_walks`, `total_strikeouts`: Component counting stats

### Automated Updates

Set up a cron job for regular updates:

```bash
# Edit crontab
crontab -e

# Run daily at 6 AM during season
0 6 * * * /path/to/baseballSOS/run_mlb_offense_quality.sh >> /path/to/baseballSOS/logs/cron.log 2>&1

# Run twice weekly (Monday and Friday at 8 AM)
0 8 * * 1,5 /path/to/baseballSOS/run_mlb_offense_quality.sh >> /path/to/baseballSOS/logs/cron.log 2>&1
```

The `run_mlb_offense_quality.sh` wrapper script automatically activates the virtual environment before execution.

## Data Source

This project uses the official **MLB Stats API** (statsapi.mlb.com):
- Real-time game data and box scores
- Team and pitcher statistics
- No API key required
- Free and publicly accessible

All data is fetched fresh on each run to ensure current results.

## Use Cases

**For Analysts:**
- Identify teams over/underperforming their underlying offensive talent
- Account for schedule strength when comparing teams
- Isolate park effects from genuine offensive quality

**For Bettors:**
- Find value in teams facing upcoming strength-of-schedule shifts
- Exploit platoon advantages using LHP/RHP splits
- Identify home/road performance discrepancies

**For Fantasy Players:**
- Target players on teams with favorable upcoming schedules
- Understand context behind raw offensive statistics
- Identify buy-low/sell-high candidates based on opponent adjustments

**For Front Offices:**
- Evaluate trade targets in context of their offensive environment
- Assess whether offensive improvements are sustainable
- Guide roster construction based on platoon splits

## Technical Notes

- **Only regular season games** are included (no Spring Training, All-Star, playoffs)
- **Minimum sample sizes**: Park factors require 10+ games at a venue
- **Processing time**: 2-4 minutes for a full season (~2,430 games)
- **Split calculations**:
  - Overall and pitcher handedness splits: Include both opponent and park adjustments
  - Home/away splits: Include only opponent adjustments (to isolate venue effects)

## Future Enhancements

Potential additions:
- Rolling 30-day trend analysis
- Interactive visualizations (matplotlib/seaborn)
- Day/night game splits
- Weather-adjusted metrics
- REST API for programmatic access
- Historical trend comparisons across multiple seasons

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - feel free to use and modify for your own analysis.

## Acknowledgments

- MLB Stats API for comprehensive data access
- Sabermetric community for linear weights research
- FanGraphs and Baseball Prospectus for RA9- methodology
