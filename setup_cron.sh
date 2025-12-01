#!/bin/bash
# Sample cron job setup for MLB Offensive Rankings
# 
# This script can be added to your crontab to automatically run
# the MLB offensive rankings calculator at scheduled times
#
# To install:
# 1. Make this script executable: chmod +x setup_cron.sh
# 2. Edit your crontab: crontab -e
# 3. Add one of the example lines below

# Get the directory where this script is located
SCRIPT_DIR="/Users/alexstillwell/Documents/_ML/baseballSOS"
WRAPPER_SCRIPT="$SCRIPT_DIR/run_mlb_offense_quality.sh"
LOG_DIR="$SCRIPT_DIR/logs"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Example cron job entries (uncomment and modify as needed):

# Run every day at 6 AM during baseball season
# 0 6 * 4-10 * $WRAPPER_SCRIPT >> $LOG_DIR/rankings.log 2>&1

# Run every Monday and Friday at 8 AM
# 0 8 * * 1,5 $WRAPPER_SCRIPT >> $LOG_DIR/rankings.log 2>&1

# Run twice per month (1st and 15th) at 9 AM
# 0 9 1,15 * * $WRAPPER_SCRIPT >> $LOG_DIR/rankings.log 2>&1

# Run every week on Sunday at 7 AM
# 0 7 * * 0 $WRAPPER_SCRIPT >> $LOG_DIR/rankings.log 2>&1

echo "Cron job examples for MLB Offensive Rankings:"
echo ""
echo "Note: These commands use run_mlb_offense_quality.sh which handles virtual environment activation"
echo ""
echo "1. Daily during season (6 AM):"
echo "   0 6 * 4-10 * $WRAPPER_SCRIPT >> $LOG_DIR/rankings.log 2>&1"
echo ""
echo "2. Twice weekly (Mon/Fri at 8 AM):"
echo "   0 8 * * 1,5 $WRAPPER_SCRIPT >> $LOG_DIR/rankings.log 2>&1"
echo ""
echo "3. Weekly (Sunday at 7 AM):"
echo "   0 7 * * 0 $WRAPPER_SCRIPT >> $LOG_DIR/rankings.log 2>&1"
echo ""
echo "To add to crontab:"
echo "  1. Run: crontab -e"
echo "  2. Add one of the lines above"
echo "  3. Save and exit"
echo ""
echo "To view current crontab:"
echo "  crontab -l"
echo ""
echo "To verify Python path:"
echo "  which python3"

