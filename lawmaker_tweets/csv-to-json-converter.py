#!/usr/bin/env python3
"""
Convert lawmaker tweet CSV data to optimized JSON format for web app.
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
    # Pattern for House members: "Rep. Name Party-State-District"
    # Pattern for Senators: "Sen. Name Party-State"
    
    # Remove Rep./Sen. prefix
    name = display_name.replace('Rep. ', '').replace('Sen. ', '')
    
    # Extract party-state-district info
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
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'data'), exist_ok=True)
    
    # Data structures
    lawmakers = {}
    monthly_data = defaultdict(list)
    aggregated_data = defaultdict(lambda: defaultdict(int))
    issues = set()
    
    # Read CSV file
    print(f"Reading CSV file: {csv_file}")
    row_count = 0
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            row_count += 1
            if row_count % 10000 == 0:
                print(f"Processed {row_count} rows...")
            
            person_id = row['person_id']
            
            # Parse lawmaker info if not already stored
            if person_id not in lawmakers:
                parsed = parse_display_name(row['display_name'])
                if parsed:
                    lawmakers[person_id] = {
                        'person_id': int(person_id),
                        'display_name': row['display_name'],
                        'chamber': row['chamber'],
                        'party_name': row['party_name'],
                        'party': parsed['party'],
                        'state': parsed['state'],
                        'district': parsed['district'],
                        'full_name': parsed['full_name']
                    }
            
            # Add issue to set
            issues.add(row['issue_name'])
            
            # Create month key (YYYY-MM format)
            # The CSV has separate year and month columns
            year = row['year']
            month_name = row['month']  # This appears to be month name like "July"
            
            # Convert month name to number
            month_map = {
                'January': 1, 'February': 2, 'March': 3, 'April': 4,
                'May': 5, 'June': 6, 'July': 7, 'August': 8,
                'September': 9, 'October': 10, 'November': 11, 'December': 12
            }
            
            month_num = month_map.get(month_name, 1)  # Default to 1 if not found
            month_key = f"{year}-{month_num}"
            
            # Aggregate data by person_id, issue, and month
            agg_key = (person_id, row['issue_name'], month_key)
            aggregated_data[month_key][agg_key] += 1
    
    print(f"Total rows processed: {row_count}")
    print(f"Total lawmakers: {len(lawmakers)}")
    print(f"Total issues: {len(issues)}")
    
    # Save lawmakers metadata
    lawmakers_file = os.path.join(output_dir, 'data', 'lawmakers.json')
    with open(lawmakers_file, 'w', encoding='utf-8') as f:
        json.dump(list(lawmakers.values()), f, ensure_ascii=False, separators=(',', ':'))
    print(f"Saved lawmakers to: {lawmakers_file}")
    
    # Save aggregated data by month
    months = sorted(aggregated_data.keys())
    
    for month in months:
        month_records = []
        
        for (person_id, issue_name, month_key), count in aggregated_data[month].items():
            month_records.append({
                'person_id': int(person_id),
                'issue_name': issue_name,
                'month': month_key,
                'count': count
            })
        
        # Save compressed monthly data
        month_file = os.path.join(output_dir, 'data', f'tweets-{month}.json.gz')
        json_data = json.dumps(month_records, ensure_ascii=False, separators=(',', ':'))
        
        with gzip.open(month_file, 'wt', encoding='utf-8') as f:
            f.write(json_data)
        
        print(f"Saved {len(month_records)} records to: {month_file}")
    
    # Create index file
    index_data = {
        'months': months,
        'totalRecords': sum(len(records) for records in aggregated_data.values()),
        'lawmakers': len(lawmakers),
        'issues': sorted(list(issues))
    }
    
    index_file = os.path.join(output_dir, 'data', 'index.json')
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    print(f"Saved index to: {index_file}")
    
    # Create a demo/default view with most recent data
    recent_months = months[-3:] if len(months) >= 3 else months
    default_data = []
    
    for month in recent_months:
        for (person_id, issue_name, month_key), count in aggregated_data[month].items():
            if issue_name == 'All' or month_key in recent_months:  # Customize as needed
                default_data.append({
                    'person_id': int(person_id),
                    'issue_name': issue_name,
                    'month': month_key,
                    'count': count
                })
    
    default_file = os.path.join(output_dir, 'data', 'default-view.json')
    with open(default_file, 'w', encoding='utf-8') as f:
        json.dump(default_data, f, ensure_ascii=False, separators=(',', ':'))
    print(f"Saved default view to: {default_file}")
    
    # Print summary statistics
    print("\n=== Conversion Summary ===")
    print(f"Total lawmakers: {len(lawmakers)}")
    print(f"Total months: {len(months)}")
    print(f"Total issues: {len(issues)}")
    print(f"Date range: {months[0]} to {months[-1]}")
    
    # Calculate file sizes
    total_size = 0
    for month in months:
        month_file = os.path.join(output_dir, 'data', f'tweets-{month}.json.gz')
        if os.path.exists(month_file):
            size = os.path.getsize(month_file)
            total_size += size
            print(f"  {month}: {size / 1024:.1f} KB")
    
    print(f"Total compressed size: {total_size / 1024 / 1024:.1f} MB")
    
    # Create sample HTML update for data loading
    create_data_loader_js(output_dir)

def create_data_loader_js(output_dir):
    """Create a JavaScript file with the data loading logic."""
    
    js_content = '''// Data loader for lawmaker Twitter activity
class DataLoader {
    constructor() {
        this.lawmakers = new Map();
        this.tweetData = new Map();
        this.loadedMonths = new Set();
        this.index = null;
        this.issues = [];
    }
    
    async init() {
        // Load index and lawmakers (small files)
        const [indexResponse, lawmakersResponse] = await Promise.all([
            fetch('data/index.json'),
            fetch('data/lawmakers.json')
        ]);
        
        this.index = await indexResponse.json();
        const lawmakersArray = await lawmakersResponse.json();
        
        // Create lawmakers map
        lawmakersArray.forEach(lm => {
            this.lawmakers.set(lm.person_id, lm);
        });
        
        // Store issues list
        this.issues = this.index.issues || [];
        
        // Load last 3 months by default
        const recentMonths = this.index.months.slice(-3);
        await this.loadMonths(recentMonths);
    }
    
    async loadMonths(months) {
        const monthsToLoad = months.filter(m => !this.loadedMonths.has(m));
        
        if (monthsToLoad.length === 0) return;
        
        // Show loading indicator
        console.log(`Loading data for months: ${monthsToLoad.join(', ')}`);
        
        // Load compressed monthly data
        const promises = monthsToLoad.map(async (month) => {
            const response = await fetch(`data/tweets-${month}.json.gz`);
            const compressed = await response.arrayBuffer();
            
            // Decompress in browser
            const decompressed = await this.decompress(compressed);
            const data = JSON.parse(decompressed);
            
            // Store in memory
            data.forEach(record => {
                const key = `${record.person_id}_${record.issue_name}_${record.month}`;
                this.tweetData.set(key, record);
            });
            
            this.loadedMonths.add(month);
        });
        
        await Promise.all(promises);
    }
    
    async decompress(compressed) {
        // Use browser's native decompression
        const ds = new DecompressionStream('gzip');
        const decompressedStream = new Response(compressed).body.pipeThrough(ds);
        return new Response(decompressedStream).text();
    }
    
    getFilteredData(filters) {
        const { startDate, endDate, issue, chamber, party } = filters;
        
        // Ensure we have the needed months loaded
        const neededMonths = this.getMonthsInRange(startDate, endDate);
        const unloadedMonths = neededMonths.filter(m => !this.loadedMonths.has(m));
        
        if (unloadedMonths.length > 0) {
            // Return promise that loads data first
            return this.loadMonths(unloadedMonths).then(() => this.filterData(filters));
        }
        
        return Promise.resolve(this.filterData(filters));
    }
    
    filterData(filters) {
        const aggregated = new Map();
        
        for (const [key, record] of this.tweetData) {
            const lawmaker = this.lawmakers.get(record.person_id);
            if (!lawmaker) continue;
            
            // Apply filters
            if (filters.issue !== 'All' && record.issue_name !== filters.issue) continue;
            if (filters.chamber !== 'Both Chambers' && lawmaker.chamber !== filters.chamber) continue;
            if (filters.party !== 'All Parties' && !lawmaker.party_name.includes(filters.party)) continue;
            
            // Check date range
            const [year, month] = record.month.split('-').map(Number);
            const recordDate = new Date(year, month - 1, 1);
            
            if (recordDate < filters.startDate || recordDate > filters.endDate) continue;
            
            // Aggregate by person
            const personId = record.person_id;
            if (!aggregated.has(personId)) {
                aggregated.set(personId, {
                    person_id: personId,
                    display_name: lawmaker.display_name,
                    party_clean: lawmaker.party_name,
                    posts: 0
                });
            }
            aggregated.get(personId).posts += record.count;
        }
        
        return Array.from(aggregated.values());
    }
    
    getMonthsInRange(startDate, endDate) {
        const months = [];
        const current = new Date(startDate);
        current.setDate(1); // Start at beginning of month
        
        while (current <= endDate) {
            const year = current.getFullYear();
            const month = current.getMonth() + 1;
            months.push(`${year}-${month}`);
            current.setMonth(current.getMonth() + 1);
        }
        
        return months;
    }
    
    getDateRange() {
        if (!this.index || !this.index.months || this.index.months.length === 0) {
            return { start: new Date(), end: new Date() };
        }
        
        const firstMonth = this.index.months[0];
        const lastMonth = this.index.months[this.index.months.length - 1];
        
        const [startYear, startMonth] = firstMonth.split('-').map(Number);
        const [endYear, endMonth] = lastMonth.split('-').map(Number);
        
        return {
            start: new Date(startYear, startMonth - 1, 1),
            end: new Date(endYear, endMonth - 1, 1)
        };
    }
}

// Export for use in main app
window.DataLoader = DataLoader;
'''
    
    js_file = os.path.join(output_dir, 'data-loader.js')
    with open(js_file, 'w', encoding='utf-8') as f:
        f.write(js_content)
    print(f"\nCreated data loader script: {js_file}")

if __name__ == "__main__":

    csv_file = '1_tweets_df.csv'
    output_dir = './'
    
    if not os.path.exists(csv_file):
        print(f"Error: CSV file '{csv_file}' not found")
        sys.exit(1)
    
    convert_csv_to_json(csv_file, output_dir)