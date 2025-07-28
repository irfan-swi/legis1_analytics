import pandas as pd
import json
from datetime import datetime
import re

def parse_display_name(display_name):
    """
    Parse display name like 'Sen. Maria Cantwell D-WA' to extract:
    - full_name: 'Maria Cantwell'
    - first_name: 'Maria'  
    - last_name: 'Cantwell'
    - party: 'Democrat' (from D/R/I)
    - chamber: 'senate' (from Sen./Rep.)
    """
    
    # Extract chamber
    chamber = 'senate' if display_name.startswith('Sen.') else 'house'
    
    # Remove prefix and suffix to get just the name
    # Pattern: "Sen./Rep. FirstName LastName Party-State"
    name_part = re.sub(r'^(Sen\.|Rep\.)\s+', '', display_name)
    name_part = re.sub(r'\s+[DRI]-[A-Z]{2}$', '', name_part)
    
    # Split name into parts
    name_parts = name_part.strip().split()
    
    if len(name_parts) >= 2:
        first_name = name_parts[0]
        last_name = ' '.join(name_parts[1:])  # Handle multi-part last names
        full_name = name_part.strip()
    else:
        # Fallback if parsing fails
        full_name = name_part.strip()
        first_name = name_parts[0] if name_parts else ""
        last_name = ""
    
    return {
        'chamber': chamber,
        'full_name': full_name,
        'first_name': first_name,
        'last_name': last_name
    }

def convert_csv_to_json(csv_file_path, output_file_path, congress_number=119):
    """
    Convert the staff experience CSV to the required JSON format
    """
    
    # Read the CSV file
    df = pd.read_csv(csv_file_path)
    
    # Initialize the output structure
    output_data = {
        "congress": congress_number,
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "members": []
    }
    
    # Process each row
    for _, row in df.iterrows():
        # Parse the display name to extract name components and chamber
        name_info = parse_display_name(row['display_name'])
        
        # Map party abbreviation to full name
        party_mapping = {
            'D': 'Democrat',
            'R': 'Republican', 
            'I': 'Independent'
        }
        
        # Extract party from display_name (backup) or use party_name column
        party_from_display = None
        if ' D-' in row['display_name']:
            party_from_display = 'Democrat'
        elif ' R-' in row['display_name']:
            party_from_display = 'Republican'
        elif ' I-' in row['display_name']:
            party_from_display = 'Independent'
        
        # Use party_name column if available, otherwise use parsed party
        party = party_from_display or row.get('party_name', 'Unknown')
        
        # Extract district number for House members (null for Senate)
        district = None
        if name_info['chamber'] == 'house':
            # You might need to extract this from another source since it's not in the display_name
            # For now, setting to null - you may need to join with another data source
            district = None
        
        # Create member object
        member = {
            "person_id": str(row['person_id']),
            "full_name": name_info['full_name'],
            "last_name": name_info['last_name'],
            "first_name": name_info['first_name'],
            "party": party,
            "chamber": name_info['chamber'],
            "state": row['us_state_id'],
            "district": district,
            "total_staff_experience": float(row['total_staff_experience']),
            "average_staff_experience": round(float(row['average_staff_experience']), 1),
            "staff_count": int(row['staff_count']),
            "chief_of_staff_experience": float(row['chief_of_staff_experience'])
        }
        
        output_data["members"].append(member)
    
    # Sort by last name, first name
    output_data["members"].sort(key=lambda x: (x['last_name'], x['first_name']))
    
    # Write to JSON file
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully converted {len(output_data['members'])} members to {output_file_path}")
    
    # Print sample member for verification
    if output_data["members"]:
        print("\nSample member:")
        print(json.dumps(output_data["members"][0], indent=2))
    
    return output_data

# Example usage
if __name__ == "__main__":
    # Convert the CSV file
    convert_csv_to_json(
        csv_file_path="staff_experience.csv",  # Your input CSV file
        output_file_path="congress-119-staff-experience.json",  # Output JSON file
        congress_number=119
    )
    
    # Alternative: If you want to process the data in memory (useful for data validation)
    def quick_convert_sample():
        """
        Quick test with sample data to verify the conversion works
        """
        sample_data = """person_id,Chamber,us_state_id,party_name,display_name,staff_count,total_staff_experience,average_staff_experience,chief_of_staff_experience
17,Senate,WA,Democrat,Sen. Maria Cantwell D-WA,58,333,5.74,13
25,Senate,ME,Republican,Sen. Susan Collins R-ME,51,244,4.78,13
27,Senate,TX,Republican,Sen. John Cornyn R-TX,59,420,7.11,8
30,Senate,ID,Republican,Sen. Mike Crapo R-ID,59,445,7.54,23
38,Senate,IL,Democrat,Sen. Dick Durbin D-IL,100,182,1.82,12"""
        
        # Save sample to temp file
        with open("temp_sample.csv", "w") as f:
            f.write(sample_data)
        
        # Convert
        result = convert_csv_to_json("temp_sample.csv", "sample_output.json")
        
        # Print results
        print("Sample conversion successful!")
        print(f"Converted {len(result['members'])} members")
        
        # Clean up
        import os
        os.remove("temp_sample.csv")
        
        return result
    
    # Uncomment to test with sample data:
    # quick_convert_sample()