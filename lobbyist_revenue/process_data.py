import pandas as pd
import json
import gzip
from pathlib import Path
import numpy as np

def process_lobbying_data(lobbying_csv, lobbyists_csv, output_dir):
    """
    Process lobbying data and active lobbyist counts into optimized JSON files
    """
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Read the CSV files
    print("Reading CSV files...")
    lobbying_df = pd.read_csv(lobbying_csv)
    lobbyists_df = pd.read_csv(lobbyists_csv)
    
    # Filter out deleted records
    lobbying_df = lobbying_df[lobbying_df['is_deleted'] == 0]
    
    # Create year-quarter string for easier grouping
    lobbying_df['year_quarter'] = lobbying_df['report_year'].astype(str) + '-Q' + lobbying_df['report_quarter'].astype(str)
    
    # Identify in-house lobbying (where firm = client)
    lobbying_df['is_in_house'] = lobbying_df['lobby_firm'] == lobbying_df['client']
    
    # Merge with lobbyist counts
    print("Merging with lobbyist counts...")
    merged_df = lobbying_df.merge(
        lobbyists_df,
        left_on='registrant_lobby_actor_id',
        right_on='registrant_lobby_actor_id',
        how='left'
    )
    
    # Handle any missing lobbyist counts (shouldn't happen, but just in case)
    merged_df['lobbyists'] = merged_df['lobbyists'].fillna(1)
    
    # Process data by year
    years = sorted(merged_df['report_year'].unique())
    print(f"Processing data for years: {years}")
    
    all_firms_data = {}
    
    for year in years:
        print(f"\nProcessing year {year}...")
        year_data = merged_df[merged_df['report_year'] == year]
        
        # Aggregate by firm
        firm_totals = year_data.groupby('lobby_firm').agg({
            'income': 'sum',
            'client': 'nunique',
            'lobbyists': 'first',  # Should be same for all records of a firm
            'registrant_lobby_actor_id': 'first'
        }).reset_index()
        
        # Calculate in-house revenue
        in_house_revenue = year_data[year_data['is_in_house']].groupby('lobby_firm')['income'].sum()
        firm_totals['in_house_revenue'] = firm_totals['lobby_firm'].map(in_house_revenue).fillna(0)
        
        # Calculate quarterly breakdowns
        quarterly = year_data.groupby(['lobby_firm', 'report_quarter']).agg({
            'income': 'sum'
        }).reset_index()
        
        # Pivot quarterly data
        quarterly_pivot = quarterly.pivot_table(
            index='lobby_firm',
            columns='report_quarter',
            values='income',
            fill_value=0
        )
        
        # Merge quarterly data
        firm_totals = firm_totals.merge(quarterly_pivot, left_on='lobby_firm', right_index=True, how='left')
        
        # Calculate derived metrics
        firm_totals['total_revenue'] = firm_totals['income']
        firm_totals['external_revenue'] = firm_totals['total_revenue'] - firm_totals['in_house_revenue']
        firm_totals['revenue_per_lobbyist'] = firm_totals['total_revenue'] / firm_totals['lobbyists']
        firm_totals['in_house_percentage'] = firm_totals['in_house_revenue'] / firm_totals['total_revenue']
        firm_totals['in_house_percentage'] = firm_totals['in_house_percentage'].fillna(0)
        
        # Get top clients for each firm
        print(f"Processing top clients for {len(firm_totals)} firms...")
        clients_data = {}
        
        for firm in firm_totals['lobby_firm'].unique():
            firm_data = year_data[year_data['lobby_firm'] == firm]
            
            # Get top 10 clients by income
            top_clients = firm_data.groupby('client').agg({
                'income': 'sum',
                'is_in_house': 'first'
            }).reset_index()
            
            top_clients = top_clients.sort_values('income', ascending=False).head(10)
            
            clients_data[firm] = [
                {
                    'name': row['client'],
                    'amount': int(row['income']),
                    'isInHouse': bool(row['is_in_house'])
                }
                for _, row in top_clients.iterrows()
            ]
        
        # Prepare firm data for JSON
        firms_json = []
        for _, firm in firm_totals.iterrows():
            firm_dict = {
                'firm_id': f"f{firm['registrant_lobby_actor_id']}",
                'name': firm['lobby_firm'],
                'year': int(year),
                'lobbyists': int(firm['lobbyists']),
                'totalRevenue': int(firm['total_revenue']),
                'externalRevenue': int(firm['external_revenue']),
                'inHouseRevenue': int(firm['in_house_revenue']),
                'inHousePercentage': float(firm['in_house_percentage']),
                'revenuePerLobbyist': int(firm['revenue_per_lobbyist']),
                'numClients': int(firm['client']),
                'quarterlyRevenue': {
                    f'{year}-Q1': int(firm.get(1, 0)),
                    f'{year}-Q2': int(firm.get(2, 0)),
                    f'{year}-Q3': int(firm.get(3, 0)),
                    f'{year}-Q4': int(firm.get(4, 0))
                },
                'clients': clients_data.get(firm['lobby_firm'], [])
            }
            firms_json.append(firm_dict)
        
        # Sort by revenue per lobbyist (descending)
        firms_json.sort(key=lambda x: x['revenuePerLobbyist'], reverse=True)
        
        # Save to compressed JSON
        output_file = Path(output_dir) / f'firms_{year}.json.gz'
        print(f"Saving {len(firms_json)} firms to {output_file}")
        
        with gzip.open(output_file, 'wt', encoding='utf-8') as f:
            json.dump(firms_json, f, separators=(',', ':'))  # Compact JSON
        
        # Also save uncompressed for development/debugging
        output_file_uncompressed = Path(output_dir) / f'firms_{year}.json'
        with open(output_file_uncompressed, 'w', encoding='utf-8') as f:
            json.dump(firms_json, f, indent=2)
        
        all_firms_data[year] = firms_json
    
    # Create metadata file
    metadata = {
        "last_updated": pd.Timestamp.now().isoformat(),
        "years": [int(y) for y in years],
        "total_records": len(lobbying_df),
        "total_firms": len(lobbyists_df),
        "data_version": "1.0",
        "firm_counts_by_year": {
            int(year): len(data) for year, data in all_firms_data.items()
        }
    }
    
    metadata_file = Path(output_dir) / 'metadata.json'
    print(f"\nSaving metadata to {metadata_file}")
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Print summary statistics
    print("\n=== Processing Complete ===")
    print(f"Years processed: {years}")
    for year in years:
        print(f"Year {year}: {metadata['firm_counts_by_year'][year]} firms")
        if year in all_firms_data:
            top_5 = all_firms_data[year][:5]
            print(f"  Top 5 firms by revenue per lobbyist:")
            for i, firm in enumerate(top_5, 1):
                print(f"    {i}. {firm['name']}: ${firm['revenuePerLobbyist']:,}/lobbyist")
    
    return metadata

# Example usage
if __name__ == "__main__":
    # Process the data
    metadata = process_lobbying_data(
        lobbying_csv='lobbying.csv',
        lobbyists_csv='active_lobbyists.csv',
        output_dir='data'
    )
    
    print("\nFile sizes:")
    import os
    for file in Path('data').glob('*.json*'):
        size = os.path.getsize(file)
        print(f"  {file.name}: {size:,} bytes ({size/1024/1024:.2f} MB)")