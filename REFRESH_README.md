# Analytics Refresh Automation

Automated script to refresh data for legislative analytics apps.

## Setup

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Database Connection:**
   - Your config file `refresh_config.json` is already set up
   - This file is gitignored to protect credentials
   - Template available in `refresh_config.template.json`

## Usage

### Refresh All Apps
```bash
python refresh_analytics.py
```

### Refresh Specific Apps
```bash
python refresh_analytics.py --apps lawmaker_tweets
python refresh_analytics.py --apps lawmaker_tweets,congressional_tweet_sentiment
```

### Dry Run (Preview Without Executing)
```bash
python refresh_analytics.py --dry-run
```

### Skip Git Push (Commit Locally Only)
```bash
python refresh_analytics.py --no-push
```

### Verbose Logging
```bash
python refresh_analytics.py --verbose
```

## What the Script Does

For each analytics app:

1. ✓ Connects to SQL Server
2. ✓ Executes SQL query from config
3. ✓ Saves CSV to local directory
4. ✓ Backs up old data files (renamed with `.old`)
5. ✓ Runs data conversion script (CSV → JSON/Parquet)
6. ✓ Verifies new files were created
7. ✓ Deletes backup files
8. ✓ Commits to git (excluding CSV files)
9. ✓ Pushes to GitHub

## Safety Features

- **Dry Run Mode**: Preview all actions without executing
- **Automatic Backups**: Old files renamed to `.old` before processing
- **Rollback on Failure**: Backups restored if conversion fails
- **Git Exclusions**: CSV files never committed (kept local only)
- **Comprehensive Logging**: All actions logged to `refresh_log.txt`

## Scheduled Daily Refresh

To run this automatically every day:

### macOS/Linux (cron)
```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 6 AM)
0 6 * * * cd /Users/irfanhussain/Desktop/legis1_analytics && /usr/bin/python3 refresh_analytics.py >> refresh_log.txt 2>&1
```

### Windows (Task Scheduler)
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to Daily
4. Action: Start a Program
   - Program: `python`
   - Arguments: `refresh_analytics.py`
   - Start in: `C:\path\to\legis1_analytics`

## Apps Currently Configured

1. **lawmaker_tweets**
   - SQL → `1_tweets_df.csv`
   - Processor: `csv-to-json-converter.py`
   - Output: JSON files in `data/`

2. **congressional_tweet_sentiment**
   - SQL → `scripts/old.csv`
   - Processor: `scripts/prepare_data.py`
   - Output: Parquet files in `data/`

## Troubleshooting

### SQL Connection Fails
- Verify server/database in `refresh_config.json`
- Check ODBC Driver 17 for SQL Server is installed
- Test credentials with SQL Server Management Studio

### Processor Script Fails
- Check CSV file was created correctly
- Run processor script manually to see detailed error
- Verify Python dependencies are installed

### Git Operations Fail
- Ensure working directory is clean before running
- Check git credentials are configured
- Verify you have push access to repository

### View Logs
```bash
tail -f refresh_log.txt
```

## Adding New Apps

To add a new analytics app to the refresh process:

1. Add SQL query to `sql_queries` in config
2. Add app configuration to `apps` in config
3. Ensure app has a processor script
4. Test with `--dry-run` first

Example config:
```json
{
  "new_app": {
    "enabled": true,
    "path": "new_app",
    "sql_query_key": "new_app_query",
    "csv_output": "data.csv",
    "processor_script": "process.py",
    "processor_cwd": "new_app",
    "data_dir": "new_app/data",
    "data_patterns": ["*.json"],
    "data_exclude_patterns": [],
    "git_exclude": ["new_app/data.csv"],
    "git_commit_message": "refreshing new_app"
  }
}
```
