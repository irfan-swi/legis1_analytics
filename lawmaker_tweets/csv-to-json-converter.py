#!/usr/bin/env python3
"""
Convert lawmaker tweet CSV data to optimized JSON format for web app.
Tracks UNIQUE tweets both per-issue and overall to avoid double-counting.
Usage: python convert_tweets_data.py input.csv output_directory/
"""

import csv
import json
import gzip
import os
import sys
from collections import defaultdict
from datetime import datetime
import re

def parse_display_name(display_name):
    """Extract name, party, state, and district from display name."""
    name = display_name.replace('Rep. ', '').replace('Sen. ', '')
    match = re.search(r'(.+?)\s+([A-Z])-([A-Z]{2})(?:-(\d+))?', name)
    
    if match:
        full_name = match.group(1).strip()
        party = match.group(2)
        state = match.group(3)
        district = match.group(4)
        
        return {
            'full_name': full_name,
            'party': party,
            'state': state,
            'district': int(district) if district else None
        }
    
    return None

def convert_csv_to_json(csv_file, output_dir):
    """Convert CSV file to optimized JSON format."""
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'data'), exist_ok=True)
    
    lawmakers = {}
    # Track unique tweets per (person, issue, month) for issue-specific counts
    unique_tweets_by_issue = defaultdict(lambda: defaultdict(set))
    # Track unique tweets per (person, month) for "All Issues" counts  
    unique_tweets_overall = defaultdict(lambda: defaultdict(set))
    issues = set()
    
    print(f"Reading CSV file: {csv_file}")
    
    # First, detect the delimiter and check the header
    with open(csv_file, 'r', encoding='utf-8', newline='') as f:
        # Read first line to check format
        first_line = f.readline()
        print(f"First line: {repr(first_line[:100])}")
        
        # Detect delimiter
        if '\t' in first_line:
            delimiter = '\t'
            print("Detected tab-delimited file")
        elif ',' in first_line:
            delimiter = ','
            print("Detected comma-delimited file")
        else:
            print("ERROR: Could not detect delimiter")
            sys.exit(1)
    
    # Now read the actual data
    row_count = 0
    with open(csv_file, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        
        # Check if required columns exist
        fieldnames = reader.fieldnames
        print(f"Columns found: {fieldnames}")
        
        required_cols = ['person_id', 'comm_content_id', 'issue_name', 'year', 'month', 'display_name']
        missing_cols = [col for col in required_cols if col not in fieldnames]
        
        if missing_cols:
            print(f"ERROR: Missing required columns: {missing_cols}")
            print(f"Available columns: {fieldnames}")
            sys.exit(1)
        
        for row in reader:
            row_count += 1
            if row_count % 10000 == 0:
                print(f"Processed {row_count} rows...")
            
            person_id = row['person_id'].strip()
            comm_content_id = row['comm_content_id'].strip()
            
            if not person_id or not comm_content_id:
                continue  # Skip rows with empty values
            
            if person_id not in lawmakers:
                parsed = parse_display_name(row['display_name'])
                if parsed:
                    lawmakers[person_id] = {
                        'person_id': int(person_id),
                        'display_name': row['display_name'],
                        'chamber': row.get('chamber', ''),
                        'party_name': row.get('party_name', ''),
                        'party': parsed['party'],
                        'state': parsed['state'],
                        'district': parsed['district'],
                        'full_name': parsed['full_name']
                    }
            
            issue_name = row['issue_name'].strip()
            issues.add(issue_name)
            
            year = row['year'].strip()
            month_name = row['month'].strip()
            
            month_map = {
                'January': 1, 'February': 2, 'March': 3, 'April': 4,
                'May': 5, 'June': 6, 'July': 7, 'August': 8,
                'September': 9, 'October': 10, 'November': 11, 'December': 12
            }
            
            month_num = month_map.get(month_name, 1)
            month_key = f"{year}-{month_num}"
            
            # Track by issue (for issue-specific filtering)
            issue_key = (person_id, issue_name)
            unique_tweets_by_issue[month_key][issue_key].add(comm_content_id)
            
            # Track overall (for "All Issues" counts - this is the TRUE unique count)
            person_key = (person_id, 'All')
            unique_tweets_overall[month_key][person_key].add(comm_content_id)
    
    print(f"\nTotal rows processed: {row_count}")
    print(f"Total lawmakers: {len(lawmakers)}")
    print(f"Total issues: {len(issues)}")
    
    # Save lawmakers metadata
    lawmakers_file = os.path.join(output_dir, 'data', 'lawmakers.json')
    with open(lawmakers_file, 'w', encoding='utf-8') as f:
        json.dump(list(lawmakers.values()), f, ensure_ascii=False, separators=(',', ':'))
    print(f"Saved lawmakers to: {lawmakers_file}")
    
    # Sort months chronologically
    months = sorted(unique_tweets_by_issue.keys(), key=lambda x: tuple(map(int, x.split('-'))))
    
    total_records = 0
    for month in months:
        month_records = []
        
        # Add per-issue records
        for (person_id, issue_name), tweet_ids in unique_tweets_by_issue[month].items():
            unique_count = len(tweet_ids)
            month_records.append({
                'person_id': int(person_id),
                'issue_name': issue_name,
                'month': month,
                'count': unique_count
            })
            total_records += 1
        
        # Add "All" records with true unique counts
        for (person_id, _), tweet_ids in unique_tweets_overall[month].items():
            unique_count = len(tweet_ids)
            month_records.append({
                'person_id': int(person_id),
                'issue_name': 'All',
                'month': month,
                'count': unique_count
            })
            total_records += 1
        
        # Save compressed monthly data
        month_file = os.path.join(output_dir, 'data', f'tweets-{month}.json.gz')
        json_data = json.dumps(month_records, ensure_ascii=False, separators=(',', ':'))
        
        with gzip.open(month_file, 'wt', encoding='utf-8') as f:
            f.write(json_data)
        
        print(f"Saved {len(month_records)} records to: {month_file}")
    
    # Create index file
    index_data = {
        'months': months,
        'totalRecords': total_records,
        'lawmakers': len(lawmakers),
        'issues': sorted(list(issues))
    }
    
    index_file = os.path.join(output_dir, 'data', 'index.json')
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    print(f"Saved index to: {index_file}")
    
    # Print summary statistics
    print("\n=== Conversion Summary ===")
    print(f"Total lawmakers: {len(lawmakers)}")
    print(f"Total months: {len(months)}")
    print(f"Total issues: {len(issues)}")
    if months:
        print(f"Date range: {months[0]} to {months[-1]}")
    
    # Calculate file sizes
    total_size = 0
    for month in months:
        month_file = os.path.join(output_dir, 'data', f'tweets-{month}.json.gz')
        if os.path.exists(month_file):
            size = os.path.getsize(month_file)
            total_size += size
    
    print(f"Total compressed size: {total_size / 1024 / 1024:.1f} MB")
    
    # Verification: Check Nancy Mace's data if present
    nancy_mace_id = '282851'
    if nancy_mace_id in lawmakers:
        print(f"\n=== Verification for Nancy Mace (person_id={nancy_mace_id}) ===")
        for month in months[-3:]:  # Check last 3 months
            if month in unique_tweets_overall:
                for (pid, _), tweets in unique_tweets_overall[month].items():
                    if pid == nancy_mace_id:
                        print(f"{month}: {len(tweets)} unique tweets")
                        break

if __name__ == "__main__":
    csv_file = '1_tweets_df.csv'
    output_dir = './'
    
    if not os.path.exists(csv_file):
        print(f"Error: CSV file '{csv_file}' not found")
        sys.exit(1)
    
    convert_csv_to_json(csv_file, output_dir)
