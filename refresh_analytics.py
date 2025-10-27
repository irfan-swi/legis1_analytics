#!/usr/bin/env python3
"""
Analytics Refresh Automation Script
Automates the data refresh process for legislative analytics apps.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import shutil
import glob

try:
    import pyodbc
    import pandas as pd
except ImportError as e:
    print(f"Error: Missing required package: {e}")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)


class AnalyticsRefresher:
    """Main class for refreshing analytics data."""

    def __init__(self, config_path: str = "refresh_config.json", dry_run: bool = False,
                 verbose: bool = False, no_push: bool = False):
        self.config_path = config_path
        self.dry_run = dry_run
        self.no_push = no_push
        self.config = self._load_config()
        self.repo_root = Path(__file__).parent.absolute()
        self.backup_files = []

        # Setup logging
        self._setup_logging(verbose or self.config.get('logging', {}).get('verbose', False))

    def _load_config(self) -> dict:
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Configuration file '{self.config_path}' not found.")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in configuration file: {e}")
            sys.exit(1)

    def _setup_logging(self, verbose: bool):
        """Setup logging configuration."""
        log_file = self.config.get('logging', {}).get('log_file', 'refresh_log.txt')
        log_path = self.repo_root / log_file

        # Create logger
        self.logger = logging.getLogger('AnalyticsRefresher')
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)

        # File handler
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def log_info(self, message: str):
        """Log info message."""
        self.logger.info(f"{'[DRY RUN] ' if self.dry_run else ''}{message}")

    def log_error(self, message: str):
        """Log error message."""
        self.logger.error(f"{'[DRY RUN] ' if self.dry_run else ''}{message}")

    def log_success(self, message: str):
        """Log success message."""
        self.logger.info(f"{'[DRY RUN] ' if self.dry_run else ''}✓ {message}")

    def _get_sql_connection(self):
        """Create SQL Server connection."""
        sql_config = self.config['sql_server']

        # Build connection string
        if sql_config['auth_method'] == 'sql':
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={sql_config['server']};"
                f"DATABASE={sql_config['database']};"
                f"UID={sql_config['username']};"
                f"PWD={sql_config['password']}"
            )
        else:  # Windows authentication
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={sql_config['server']};"
                f"DATABASE={sql_config['database']};"
                f"Trusted_Connection=yes;"
            )

        try:
            return pyodbc.connect(conn_str)
        except pyodbc.Error as e:
            self.log_error(f"Failed to connect to SQL Server: {e}")
            raise

    def _execute_sql_query(self, query: str) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame."""
        self.log_info("Connecting to SQL Server...")

        if self.dry_run:
            self.log_info(f"Would execute query: {query[:100]}...")
            return pd.DataFrame()  # Return empty DataFrame in dry-run

        try:
            conn = self._get_sql_connection()
            self.log_info("Executing query...")
            df = pd.read_sql(query, conn)
            conn.close()
            return df
        except Exception as e:
            self.log_error(f"SQL query failed: {e}")
            raise

    def _backup_data_files(self, app_name: str, app_config: dict) -> List[Path]:
        """Backup existing data files by renaming them with .old extension."""
        data_dir = self.repo_root / app_config['data_dir']

        if not data_dir.exists():
            self.log_info(f"  Data directory does not exist yet: {data_dir}")
            return []

        backed_up_files = []
        patterns = app_config.get('data_patterns', [])
        exclude_patterns = app_config.get('data_exclude_patterns', [])

        self.log_info(f"  Backing up old data files...")

        for pattern in patterns:
            for file_path in data_dir.glob(pattern):
                # Skip excluded files
                if any(file_path.match(exclude) for exclude in exclude_patterns):
                    continue

                backup_path = file_path.with_suffix(file_path.suffix + '.old')

                if not self.dry_run:
                    if backup_path.exists():
                        backup_path.unlink()  # Remove old backup
                    file_path.rename(backup_path)

                backed_up_files.append((file_path, backup_path))
                self.log_info(f"    Backed up: {file_path.name} → {backup_path.name}")

        self.log_info(f"  Backed up {len(backed_up_files)} files")
        return backed_up_files

    def _restore_backups(self, backed_up_files: List[tuple]):
        """Restore backed up files in case of failure."""
        self.log_info("  Rolling back: Restoring backup files...")

        for original_path, backup_path in backed_up_files:
            if not self.dry_run and backup_path.exists():
                if original_path.exists():
                    original_path.unlink()
                backup_path.rename(original_path)
                self.log_info(f"    Restored: {original_path.name}")

    def _delete_backups(self, backed_up_files: List[tuple]):
        """Delete backup files after successful processing."""
        self.log_info("  Deleting backup files...")

        for _, backup_path in backed_up_files:
            if not self.dry_run and backup_path.exists():
                backup_path.unlink()
                self.log_info(f"    Deleted: {backup_path.name}")

    def _run_processor_script(self, app_name: str, app_config: dict):
        """Run the data processing script for the app."""
        script_path = app_config['processor_script']
        cwd = self.repo_root / app_config['processor_cwd']

        self.log_info(f"  Running processor script: {script_path}")

        if self.dry_run:
            self.log_info(f"  Would run: python {script_path} in {cwd}")
            return

        try:
            result = subprocess.run(
                [sys.executable, Path(script_path).name],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )

            # Log script output
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    self.log_info(f"    {line}")

        except subprocess.CalledProcessError as e:
            self.log_error(f"  Processor script failed with code {e.returncode}")
            if e.stdout:
                self.log_error(f"  STDOUT: {e.stdout}")
            if e.stderr:
                self.log_error(f"  STDERR: {e.stderr}")
            raise

    def _verify_new_files(self, app_config: dict) -> bool:
        """Verify that new data files were created."""
        data_dir = self.repo_root / app_config['data_dir']
        patterns = app_config.get('data_patterns', [])

        if self.dry_run:
            return True

        file_count = 0
        for pattern in patterns:
            # Count files that don't have .old extension
            for file_path in data_dir.glob(pattern):
                if not file_path.name.endswith('.old'):
                    file_count += 1

        self.log_info(f"  Verified {file_count} new data files created")
        return file_count > 0

    def _git_operations(self, app_name: str, app_config: dict):
        """Perform git operations: add, commit, push."""
        commit_message = app_config['git_commit_message']
        exclude_files = app_config.get('git_exclude', [])

        self.log_info(f"  Performing git operations...")

        if self.dry_run:
            self.log_info(f"  Would run: git add .")
            for exclude in exclude_files:
                self.log_info(f"  Would run: git reset -- {exclude}")
            self.log_info(f"  Would run: git commit -m '{commit_message}'")
            if not self.no_push:
                self.log_info(f"  Would run: git push")
            return

        try:
            # Git add all
            subprocess.run(['git', 'add', '.'], cwd=self.repo_root, check=True, capture_output=True)
            self.log_info(f"    git add .")

            # Unstage excluded files
            for exclude in exclude_files:
                try:
                    subprocess.run(
                        ['git', 'reset', '--', exclude],
                        cwd=self.repo_root,
                        check=True,
                        capture_output=True
                    )
                    self.log_info(f"    git reset -- {exclude}")
                except subprocess.CalledProcessError:
                    # File might not be staged, that's okay
                    pass

            # Check if there are changes to commit
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True
            )

            if not status_result.stdout.strip():
                self.log_info("    No changes to commit")
                return

            # Commit
            subprocess.run(
                ['git', 'commit', '-m', commit_message],
                cwd=self.repo_root,
                check=True,
                capture_output=True
            )
            self.log_info(f"    git commit -m '{commit_message}'")

            # Push
            if not self.no_push:
                subprocess.run(
                    ['git', 'push'],
                    cwd=self.repo_root,
                    check=True,
                    capture_output=True
                )
                self.log_info(f"    git push")
            else:
                self.log_info(f"    Skipping git push (--no-push flag set)")

        except subprocess.CalledProcessError as e:
            self.log_error(f"  Git operation failed: {e}")
            if e.stderr:
                self.log_error(f"  {e.stderr.decode()}")
            raise

    def refresh_app(self, app_name: str, app_config: dict) -> bool:
        """Refresh a single analytics app."""
        self.log_info(f"\n{'='*60}")
        self.log_info(f"Processing: {app_name}")
        self.log_info(f"{'='*60}")

        backed_up_files = []

        try:
            # Step 1: Execute SQL query
            query = self.config['sql_queries'][app_config['sql_query_key']]
            df = self._execute_sql_query(query)

            if not self.dry_run:
                self.log_info(f"  Retrieved {len(df):,} rows from database")

            # Step 2: Save CSV
            csv_path = self.repo_root / app_config['path'] / app_config['csv_output']
            csv_path.parent.mkdir(parents=True, exist_ok=True)

            if not self.dry_run:
                df.to_csv(csv_path, index=False)
                self.log_success(f"Saved CSV: {csv_path.relative_to(self.repo_root)}")
            else:
                self.log_info(f"  Would save CSV to: {csv_path.relative_to(self.repo_root)}")

            # Step 3: Backup old data files
            backed_up_files = self._backup_data_files(app_name, app_config)

            # Step 4: Run processor script
            self._run_processor_script(app_name, app_config)

            # Step 5: Verify new files
            if not self._verify_new_files(app_config):
                raise Exception("No new data files were created")

            # Step 6: Delete backups
            self._delete_backups(backed_up_files)

            # Step 7: Git operations
            self._git_operations(app_name, app_config)

            self.log_success(f"{app_name} refreshed successfully!\n")
            return True

        except Exception as e:
            self.log_error(f"Failed to refresh {app_name}: {e}")

            # Restore backups on failure
            if backed_up_files:
                self._restore_backups(backed_up_files)

            return False

    def refresh_all(self, app_names: Optional[List[str]] = None):
        """Refresh all or selected analytics apps."""
        start_time = datetime.now()

        self.log_info(f"\n{'#'*60}")
        self.log_info(f"Analytics Refresh Started")
        self.log_info(f"Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if self.dry_run:
            self.log_info(f"Mode: DRY RUN (no changes will be made)")
        self.log_info(f"{'#'*60}\n")

        # Get apps to refresh
        apps = self.config['apps']

        if app_names:
            # Filter to requested apps
            apps = {name: config for name, config in apps.items()
                   if name in app_names}

            if not apps:
                self.log_error(f"No valid apps found. Available: {', '.join(self.config['apps'].keys())}")
                return
        else:
            # Filter to enabled apps
            apps = {name: config for name, config in apps.items()
                   if config.get('enabled', True)}

        self.log_info(f"Apps to refresh: {', '.join(apps.keys())}\n")

        # Refresh each app
        results = {}
        for app_name, app_config in apps.items():
            success = self.refresh_app(app_name, app_config)
            results[app_name] = success

        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        self.log_info(f"\n{'#'*60}")
        self.log_info(f"Analytics Refresh Complete")
        self.log_info(f"Duration: {duration:.1f} seconds")
        self.log_info(f"{'#'*60}\n")

        self.log_info("Results:")
        for app_name, success in results.items():
            status = "✓ SUCCESS" if success else "✗ FAILED"
            self.log_info(f"  {app_name}: {status}")

        # Exit with error code if any failed
        if not all(results.values()):
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Automate analytics data refresh process',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python refresh_analytics.py                           # Refresh all enabled apps
  python refresh_analytics.py --apps lawmaker_tweets    # Refresh specific app
  python refresh_analytics.py --dry-run                 # Preview without executing
  python refresh_analytics.py --no-push                 # Skip git push
  python refresh_analytics.py --verbose                 # Verbose logging
        """
    )

    parser.add_argument(
        '--apps',
        type=str,
        help='Comma-separated list of apps to refresh (default: all enabled apps)'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='refresh_config.json',
        help='Path to configuration file (default: refresh_config.json)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview actions without executing them'
    )

    parser.add_argument(
        '--no-push',
        action='store_true',
        help='Skip git push (commit locally only)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Parse app names
    app_names = None
    if args.apps:
        app_names = [name.strip() for name in args.apps.split(',')]

    # Run refresh
    refresher = AnalyticsRefresher(
        config_path=args.config,
        dry_run=args.dry_run,
        verbose=args.verbose,
        no_push=args.no_push
    )

    refresher.refresh_all(app_names)


if __name__ == '__main__':
    main()
