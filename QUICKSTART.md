# Analytics Refresh - Quick Start

## ✅ Setup Complete!

Your analytics refresh automation is ready to use!

## Run the Refresh

### Option 1: All Apps (Recommended)
```bash
cd /Users/irfanhussain/Desktop/legis1_analytics
./refresh.sh
```

### Option 2: Specific App Only
```bash
./refresh.sh --apps lawmaker_tweets
./refresh.sh --apps congressional_tweet_sentiment
```

### Option 3: Test First (Dry Run)
```bash
./refresh.sh --dry-run
```

## What Happens

1. Connects to SQL Server (database.legisone.prod)
2. Runs queries and exports ~1.2M rows per app
3. Backs up old data files (.old extension)
4. Converts CSV → JSON/Parquet
5. Verifies new files created
6. Deletes backups
7. Commits and pushes to GitHub

**Time:** ~2-3 minutes

## Latest Run (Oct 27, 2025)

✓ **lawmaker_tweets**: 1,175,610 rows → 61 JSON files
✓ **congressional_tweet_sentiment**: 1,173,188 rows → 58 Parquet files
✓ **Duration**: 156 seconds
✓ **Pushed to GitHub**: main branch

## Daily Automation (Optional)

To run automatically at 6 AM daily:

```bash
crontab -e
```

Add this line:
```
0 6 * * * cd /Users/irfanhussain/Desktop/legis1_analytics && ./refresh.sh >> refresh_log.txt 2>&1
```

Save and exit (ESC, then :wq)

Verify:
```bash
crontab -l
```

## Logs

View the log file:
```bash
tail -f refresh_log.txt
```

## Need Help?

See `REFRESH_README.md` for full documentation.

## Files Created

- `refresh.sh` - Main script to run (uses this!)
- `refresh_analytics.py` - Python automation script
- `refresh_config.json` - Your database credentials (gitignored)
- `refresh_log.txt` - Execution logs
- `REFRESH_README.md` - Full documentation
- `QUICKSTART.md` - This file
