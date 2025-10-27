import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report
import warnings
warnings.filterwarnings('ignore')

# Define state to region mapping (Modified BEA regions)
STATE_TO_REGION = {
    # Northeast (New England + NY + NJ)
    'CT': 'Northeast', 'ME': 'Northeast', 'MA': 'Northeast', 
    'NH': 'Northeast', 'RI': 'Northeast', 'VT': 'Northeast',
    'NY': 'Northeast', 'NJ': 'Northeast',
    
    # Mid-Atlantic (formerly Mideast minus NY/NJ)
    'DE': 'Mid-Atlantic', 'DC': 'Mid-Atlantic', 'MD': 'Mid-Atlantic',
    'PA': 'Mid-Atlantic', 'VA': 'Mid-Atlantic', 'WV': 'Mid-Atlantic',
    
    # Southeast
    'AL': 'Southeast', 'AR': 'Southeast', 'FL': 'Southeast',
    'GA': 'Southeast', 'KY': 'Southeast', 'LA': 'Southeast',
    'MS': 'Southeast', 'NC': 'Southeast', 'SC': 'Southeast', 'TN': 'Southeast',
    
    # Great Lakes
    'IL': 'Great Lakes', 'IN': 'Great Lakes', 'MI': 'Great Lakes',
    'OH': 'Great Lakes', 'WI': 'Great Lakes',
    
    # Plains
    'IA': 'Plains', 'KS': 'Plains', 'MN': 'Plains',
    'MO': 'Plains', 'NE': 'Plains', 'ND': 'Plains', 'SD': 'Plains',
    
    # Southwest
    'AZ': 'Southwest', 'NM': 'Southwest', 'OK': 'Southwest', 'TX': 'Southwest',
    
    # Rocky Mountain
    'CO': 'Rocky Mountain', 'ID': 'Rocky Mountain', 'MT': 'Rocky Mountain',
    'UT': 'Rocky Mountain', 'WY': 'Rocky Mountain',
    
    # Far West
    'AK': 'Far West', 'CA': 'Far West', 'HI': 'Far West',
    'NV': 'Far West', 'OR': 'Far West', 'WA': 'Far West'
}

def preprocess_data(df):
    """
    Preprocess the congressional vote data
    """
    # Create a copy
    df_processed = df.copy()
    
    # Map states to regions
    df_processed['region'] = df_processed['state'].map(STATE_TO_REGION)
    
    # Filter to only Yes/No votes for binary classification
    df_processed = df_processed[df_processed['member_vote'].isin(['Yes', 'No'])]
    
    # Encode target variable
    df_processed['vote_binary'] = (df_processed['member_vote'] == 'Yes').astype(int)
    
    # Select feature columns
    categorical_features = ['gender', 'clean_religion', 'race_id', 'party', 'region']
    numerical_features = ['age', 'years_of_experience', 'years_of_staffer_experience', 
                         'staffer_turnover_rate']
    binary_features = ['committee_membership', 'cosponsorship_status', 
                      'is_married', 'military_service']
    
    # One-hot encode categorical variables
    df_encoded = pd.get_dummies(df_processed, columns=categorical_features, prefix=categorical_features)
    
    # Get all feature columns after encoding
    feature_cols = [col for col in df_encoded.columns if any(
        col.startswith(f"{feat}_") for feat in categorical_features
    )] + numerical_features + binary_features
    
    return df_encoded, feature_cols

def calculate_feature_importance(model, X, y, feature_names, model_type):
    """
    Calculate feature importance with percentage contribution and direction
    """
    if model_type == 'LogisticRegression':
        # For logistic regression, use coefficients
        importances = np.abs(model.coef_[0])
        directions = np.sign(model.coef_[0])
    elif model_type in ['RandomForest', 'XGBoost']:
        # For tree-based models, use feature importances
        importances = model.feature_importances_
        
        # Calculate direction by comparing mean prediction when feature is high vs low
        directions = []
        for i, feature in enumerate(feature_names):
            # Split data by median of feature
            if X[:, i].std() > 0:  # Only for features with variation
                median_val = np.median(X[:, i])
                high_mask = X[:, i] > median_val
                low_mask = X[:, i] <= median_val
                
                if high_mask.sum() > 0 and low_mask.sum() > 0:
                    mean_high = y[high_mask].mean()
                    mean_low = y[low_mask].mean()
                    direction = 1 if mean_high > mean_low else -1
                else:
                    direction = 0
            else:
                direction = 0
            directions.append(direction)
        directions = np.array(directions)
    
    # Convert to percentages
    total_importance = importances.sum()
    if total_importance > 0:
        percentages = (importances / total_importance) * 100
    else:
        percentages = np.zeros_like(importances)
    
    # Create results dataframe
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance_pct': percentages,
        'direction': ['positive' if d > 0 else 'negative' if d < 0 else 'neutral' 
                     for d in directions]
    })
    
    # Sort by importance
    importance_df = importance_df.sort_values('importance_pct', ascending=False)
    
    return importance_df

def analyze_rollcall_votes(df):
    """
    Analyze each roll call vote and generate feature importance
    """
    # Preprocess the data
    df_processed, feature_cols = preprocess_data(df)
    
    # Get unique roll call votes (including chamber)
    unique_votes = df_processed[['RollCallNumber', 'session', 'congress', 'chamber']].drop_duplicates()
    
    # Initialize results storage
    all_results = []
    
    # Initialize models
    models = {
        'LogisticRegression': LogisticRegression(max_iter=1000, random_state=42),
        'RandomForest': RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10),
        'XGBoost': XGBClassifier(n_estimators=100, random_state=42, max_depth=5, 
                                 use_label_encoder=False, eval_metric='logloss')
    }
    
    print(f"Analyzing {len(unique_votes)} unique roll call votes...")
    
    for idx, vote_row in unique_votes.iterrows():
        roll_call = vote_row['RollCallNumber']
        session = vote_row['session']
        congress = vote_row['congress']
        chamber = vote_row['chamber']
        
        # Filter data for this specific vote (including chamber)
        vote_data = df_processed[
            (df_processed['RollCallNumber'] == roll_call) & 
            (df_processed['session'] == session) & 
            (df_processed['congress'] == congress) &
            (df_processed['chamber'] == chamber)
        ]
        
        if len(vote_data) < 20:  # Skip if too few samples
            continue
            
        # Prepare features and target
        X = vote_data[feature_cols].values
        y = vote_data['vote_binary'].values
        
        # Standardize numerical features
        scaler = StandardScaler()
        numerical_indices = [feature_cols.index(feat) for feat in 
                           ['age', 'years_of_experience', 'years_of_staffer_experience', 
                            'staffer_turnover_rate']]
        X_scaled = X.copy()
        X_scaled[:, numerical_indices] = scaler.fit_transform(X[:, numerical_indices])
        
        # Train each model and get feature importance
        for model_name, model in models.items():
            try:
                # Train model
                model.fit(X_scaled, y)
                
                # Calculate feature importance
                importance_df = calculate_feature_importance(
                    model, X_scaled, y, feature_cols, model_name
                )
                
                # Add metadata
                importance_df['model'] = model_name
                importance_df['congress'] = congress
                importance_df['session'] = session
                importance_df['chamber'] = chamber
                importance_df['roll_call_number'] = roll_call
                
                # Calculate model accuracy
                y_pred = model.predict(X_scaled)
                accuracy = accuracy_score(y, y_pred)
                importance_df['model_accuracy'] = accuracy
                
                all_results.append(importance_df)
                
            except Exception as e:
                print(f"Error processing vote {roll_call} with {model_name}: {str(e)}")
                continue
    
    # Combine all results
    if all_results:
        final_results = pd.concat(all_results, ignore_index=True)
        return final_results
    else:
        return pd.DataFrame()

def main():
    # Load data
    print("Loading data...")
    df = pd.read_csv('rollcall_data.csv')
    
    print(f"Total records: {len(df)}")
    print(f"Unique lawmakers: {df['person_id'].nunique()}")
    print(f"Unique roll calls: {df['RollCallNumber'].nunique()}")
    
    # Analyze votes
    print("\nAnalyzing roll call votes...")
    results = analyze_rollcall_votes(df)
    
    if not results.empty:
        # Save results
        results.to_csv('feature_importance_results.csv', index=False)
        print(f"\nResults saved to 'feature_importance_results.csv'")
        
        # Display sample results for the first vote
        first_vote = results[['congress', 'session', 'chamber', 'roll_call_number']].iloc[0]
        sample = results[
            (results['congress'] == first_vote['congress']) & 
            (results['session'] == first_vote['session']) & 
            (results['chamber'] == first_vote['chamber']) &
            (results['roll_call_number'] == first_vote['roll_call_number'])
        ]
        
        print("\n" + "="*80)
        print(f"Sample Results - {first_vote['chamber']} Congress {first_vote['congress']}, Session {first_vote['session']}, Roll Call {first_vote['roll_call_number']}")
        print("="*80)
        
        for model_name in ['LogisticRegression', 'RandomForest', 'XGBoost']:
            model_results = sample[sample['model'] == model_name].head(10)
            if not model_results.empty:
                accuracy = model_results['model_accuracy'].iloc[0]
                print(f"\n{model_name} (Accuracy: {accuracy:.2%})")
                print("-" * 50)
                for _, row in model_results.iterrows():
                    print(f"{row['feature']:40s} {row['importance_pct']:6.2f}% ({row['direction']})")
    else:
        print("No results generated. Please check the data.")

if __name__ == "__main__":
    main()