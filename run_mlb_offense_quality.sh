#!/bin/bash
# Wrapper script for running mlb_offense_quality.py with virtual environment
# Use this script in cron jobs to ensure virtual environment is activated

# Set the script directory
SCRIPT_DIR="/Users/alexstillwell/Documents/_ML/baseballSOS"

# Change to script directory
cd "$SCRIPT_DIR" || exit 1

# Activate virtual environment
source venv/bin/activate

# Run the main script with all arguments passed to this wrapper
python mlb_offense_quality.py "$@"

# Capture exit code
EXIT_CODE=$?

# Deactivate virtual environment
deactivate

# Exit with the same code as the Python script
exit $EXIT_CODE

