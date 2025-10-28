#!/bin/bash
# Wrapper script to run analytics refresh with proper ODBC configuration

# Set ODBC configuration path
export ODBCSYSINI=~

# Run the refresh script with all passed arguments
python3 "$(dirname "$0")/refresh_analytics.py" "$@"
