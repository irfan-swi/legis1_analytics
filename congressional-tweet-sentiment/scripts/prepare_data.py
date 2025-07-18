import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import json
import os
from datetime import datetime

def prepare_tweet_data(csv_path, output_dir='../data'):
    """Convert CSV to optimized parquet files for DuckDB-WASM with consistent monthly files"""
    
    print(f"Reading {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df):,} rows")
    
    # Ensure data directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Parse dates - handle multiple possible formats
    print("Processing dates...")
    try:
        # First try YYYY-MM-DD format
        df['pub_date_parsed'] = pd.to_datetime(df['pub_date'], format='%Y-%m-%d')
        print("  Detected date format: YYYY-MM-DD")
    except:
        try:
            # Try MM/DD/YY format
            df['pub_date_parsed'] = pd.to_datetime(df['pub_date'], format='%m/%d/%y')
            print("  Detected date format: MM/DD/YY")
        except:
            # Let pandas infer the format
            df['pub_date_parsed'] = pd.to_datetime(df['pub_date'])
            print("  Using inferred date format")
    
    df['year'] = df['pub_date_parsed'].dt.year
    df['quarter'] = df['pub_date_parsed'].dt.quarter
    df['month'] = df['pub_date_parsed'].dt.month
    
    # Convert date back to string format that DuckDB can parse (ISO format)
    df['pub_date'] = df['pub_date_parsed'].dt.strftime('%Y-%m-%d')
    
    # Ensure score is float
    df['score'] = df['score'].astype(float)
    
    # Print date range
    print(f"Date range: {df['pub_date'].min()} to {df['pub_date'].max()}")
    
    # Split by year-quarter-month for consistent file structure
    print("\nCreating consistent monthly parquet files...")
    file_info = []
    
    # Group by year, quarter, and month for consistent structure
    for (year, quarter, month), group in df.groupby(['year', 'quarter', 'month']):
        # Drop temporary columns before processing
        save_df = group.drop(['pub_date_parsed', 'year', 'quarter', 'month'], axis=1)
        
        # Create consistent filename
        filename = f"tweets_{year}_Q{quarter}_M{month:02d}.parquet"
        filepath = os.path.join(output_dir, filename)
        
        # Save with optimized compression
        save_df.to_parquet(
            filepath,
            compression='snappy',
            index=False,
            engine='pyarrow'
        )
        
        file_size = os.path.getsize(filepath) / (1024 * 1024)  # MB
        file_info.append({
            'file': filename,
            'rows': len(save_df),
            'size_mb': round(file_size, 2),
            'year': int(year),
            'quarter': int(quarter),
            'month': int(month),
            'start_date': save_df['pub_date'].min(),
            'end_date': save_df['pub_date'].max()
        })
        
        print(f"  {filename}: {len(save_df):,} rows, {file_size:.1f} MB")
    
    # Create metadata file
    print("\nCreating metadata...")
    
    # Get unique values for filters
    unique_members = df.groupby(['person_id', 'display_name', 'chamber', 'us_state_id']).size().reset_index()[['person_id', 'display_name', 'chamber', 'us_state_id']]
    
    metadata = {
        'total_rows': len(df),
        'date_range': {
            'start': df['pub_date'].min(),
            'end': df['pub_date'].max()
        },
        'files': file_info,
        'columns': list(df.drop(['pub_date_parsed', 'year', 'quarter', 'month'], axis=1).columns),
        'unique_values': {
            'chambers': sorted(df['chamber'].dropna().unique().tolist()),
            'parties': sorted(df['party_name'].dropna().unique().tolist()),
            'states': sorted(df['us_state_id'].dropna().unique().tolist()),
            'issues': sorted(df['issue_name'].dropna().unique().tolist()),
            'members': len(df['display_name'].unique())
        },
        'member_list': unique_members.to_dict('records'),
        'generated_at': datetime.now().isoformat(),
        'file_structure': 'consistent_monthly'  # Flag for apps to know structure
    }
    
    metadata_path = os.path.join(output_dir, 'metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nMetadata saved to {metadata_path}")
    
    # Create a sample file for testing
    print("\nCreating sample file...")
    sample_df = df.sample(n=min(1000, len(df)), random_state=42)
    sample_df.drop(['pub_date_parsed', 'year', 'quarter', 'month'], axis=1, inplace=True)
    sample_path = os.path.join(output_dir, 'sample.parquet')
    sample_df.to_parquet(sample_path, compression='snappy', index=False)
    print(f"Sample file created with {len(sample_df)} rows")
    
    # Print summary statistics
    print("\n" + "="*50)
    print("SUMMARY STATISTICS")
    print("="*50)
    print(f"Total tweets: {len(df):,}")
    print(f"Date range: {df['pub_date'].min()} to {df['pub_date'].max()}")
    print(f"Unique members: {df['person_id'].nunique():,}")
    print(f"Unique issues: {df['issue_name'].nunique():,}")
    print(f"\nTweets by party:")
    print(df['party_name'].value_counts())
    print(f"\nTweets by chamber:")
    print(df['chamber'].value_counts())
    
    # File structure summary
    print(f"\n" + "="*50)
    print("FILE STRUCTURE")
    print("="*50)
    print(f"Structure: Consistent monthly files")
    print(f"Total files created: {len(file_info) + 2}")  # +2 for metadata and sample
    print(f"Data files: {len(file_info)}")
    print(f"Total size: {sum(f['size_mb'] for f in file_info):.1f} MB")
    
    # Show file size distribution
    sizes = [f['size_mb'] for f in file_info]
    print(f"\nFile size distribution:")
    print(f"  Smallest: {min(sizes):.1f} MB")
    print(f"  Largest: {max(sizes):.1f} MB")
    print(f"  Average: {sum(sizes)/len(sizes):.1f} MB")
    
    # Show monthly coverage
    print(f"\nMonthly coverage:")
    monthly_counts = {}
    for file_info_item in file_info:
        year_month = f"{file_info_item['year']}-{file_info_item['month']:02d}"
        monthly_counts[year_month] = file_info_item['rows']
    
    for year_month in sorted(monthly_counts.keys())[-12:]:  # Show last 12 months
        print(f"  {year_month}: {monthly_counts[year_month]:,} tweets")
    
    print("\n✅ Data preparation complete!")
    print(f"All files use consistent naming: tweets_YYYY_QQ_MNN.parquet")
    
    return metadata

if __name__ == "__main__":
    # Update this path to your CSV file location
    csv_file = "old.csv"  # Adjust path as needed
    
    # Check if file exists
    if not os.path.exists(csv_file):
        print(f"❌ Error: Could not find {csv_file}")
        print("Please update the csv_file path in this script to point to your CSV file")
    else:
        prepare_tweet_data(csv_file, '../data')