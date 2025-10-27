import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score
import shap
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

def calculate_shap_importance(model, X, feature_names, model_type, background_samples=100):
    """
    Calculate SHAP values for feature importance
    Returns both mean absolute SHAP values (importance) and mean SHAP values (direction)
    """
    try:
        if model_type == 'LogisticRegression':
            # For linear models, use exact SHAP values
            explainer = shap.LinearExplainer(model, X, feature_perturbation="interventional")
            shap_values = explainer.shap_values(X)
        elif model_type == 'RandomForest':
            # For tree models, use TreeExplainer
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X)
            # For binary classification, take values for positive class
            if isinstance(shap_values, list):
                shap_values = shap_values[1]
        elif model_type == 'XGBoost':
            # For XGBoost, use TreeExplainer
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X)
        else:
            # Fallback to KernelExplainer
            background = shap.sample(X, min(background_samples, len(X)))
            explainer = shap.KernelExplainer(model.predict_proba, background)
            shap_values = explainer.shap_values(X)
            if isinstance(shap_values, list):
                shap_values = shap_values[1]
        
        # Calculate mean absolute SHAP values (importance)
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        
        # Calculate mean SHAP values (for direction)
        mean_shap = shap_values.mean(axis=0)
        
        # Convert to percentages
        total_importance = mean_abs_shap.sum()
        if total_importance > 0:
            importance_pct = (mean_abs_shap / total_importance) * 100
        else:
            importance_pct = np.zeros_like(mean_abs_shap)
        
        # Determine direction based on mean SHAP value
        directions = ['positive' if val > 0.001 else 'negative' if val < -0.001 else 'neutral' 
                     for val in mean_shap]
        
        # Create results dataframe
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance_pct': importance_pct,
            'mean_shap_value': mean_shap,
            'mean_abs_shap_value': mean_abs_shap,
            'direction': directions
        })
        
        # Sort by importance
        importance_df = importance_df.sort_values('importance_pct', ascending=False)
        
        return importance_df, shap_values
        
    except Exception as e:
        print(f"Error calculating SHAP values: {str(e)}")
        # Fallback to coefficient/feature importance based method
        return calculate_fallback_importance(model, X, feature_names, model_type), None

def calculate_fallback_importance(model, X, feature_names, model_type):
    """
    Fallback importance calculation when SHAP fails
    """
    if model_type == 'LogisticRegression':
        importances = np.abs(model.coef_[0])
        directions = np.sign(model.coef_[0])
    else:
        importances = model.feature_importances_
        directions = np.zeros_like(importances)
    
    total_importance = importances.sum()
    if total_importance > 0:
        percentages = (importances / total_importance) * 100
    else:
        percentages = np.zeros_like(importances)
    
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance_pct': percentages,
        'mean_shap_value': directions,
        'mean_abs_shap_value': importances,
        'direction': ['positive' if d > 0 else 'negative' if d < 0 else 'neutral' 
                     for d in directions]
    })
    
    return importance_df.sort_values('importance_pct', ascending=False)

def analyze_rollcall_votes(df, save_shap_values=False):
    """
    Analyze each roll call vote using SHAP values for interpretability
    """
    # Preprocess the data
    df_processed, feature_cols = preprocess_data(df)
    
    # Get unique roll call votes (including chamber)
    unique_votes = df_processed[['RollCallNumber', 'session', 'congress', 'chamber']].drop_duplicates()
    
    # Initialize results storage
    all_results = []
    all_shap_data = []
    
    # Initialize models
    models = {
        'LogisticRegression': LogisticRegression(max_iter=1000, random_state=42),
        'RandomForest': RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10),
        'XGBoost': XGBClassifier(n_estimators=100, random_state=42, max_depth=5, 
                                 use_label_encoder=False, eval_metric='logloss')
    }
    
    print(f"Analyzing {len(unique_votes)} unique roll call votes with SHAP values...")
    print("This may take a few minutes for large datasets...\n")
    
    processed_count = 0
    for idx, vote_row in unique_votes.iterrows():
        roll_call = vote_row['RollCallNumber']
        session = vote_row['session']
        congress = vote_row['congress']
        chamber = vote_row['chamber']
        
        # Filter data for this specific vote
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
        
        # Check if we have both classes
        if len(np.unique(y)) < 2:
            continue
        
        # Standardize numerical features
        scaler = StandardScaler()
        numerical_indices = [feature_cols.index(feat) for feat in 
                           ['age', 'years_of_experience', 'years_of_staffer_experience', 
                            'staffer_turnover_rate']]
        X_scaled = X.copy()
        X_scaled[:, numerical_indices] = scaler.fit_transform(X[:, numerical_indices])
        
        # Train each model and get SHAP importance
        for model_name, model in models.items():
            try:
                # Train model
                model.fit(X_scaled, y)
                
                # Calculate SHAP-based feature importance
                importance_df, shap_values = calculate_shap_importance(
                    model, X_scaled, feature_cols, model_name
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
                
                # Add vote statistics
                importance_df['sample_size'] = len(vote_data)
                importance_df['yes_votes'] = (y == 1).sum()
                importance_df['no_votes'] = (y == 0).sum()
                
                all_results.append(importance_df)
                
                # Store SHAP values if requested
                if save_shap_values and shap_values is not None:
                    shap_df = pd.DataFrame(shap_values, columns=feature_cols)
                    shap_df['model'] = model_name
                    shap_df['congress'] = congress
                    shap_df['session'] = session
                    shap_df['chamber'] = chamber
                    shap_df['roll_call_number'] = roll_call
                    shap_df['member_index'] = range(len(shap_df))
                    all_shap_data.append(shap_df)
                
            except Exception as e:
                print(f"Error processing vote {roll_call} with {model_name}: {str(e)}")
                continue
        
        processed_count += 1
        if processed_count % 10 == 0:
            print(f"Processed {processed_count} votes...")
    
    # Combine all results
    if all_results:
        final_results = pd.concat(all_results, ignore_index=True)
        if save_shap_values and all_shap_data:
            final_shap = pd.concat(all_shap_data, ignore_index=True)
            return final_results, final_shap
        return final_results, None
    else:
        return pd.DataFrame(), None

def analyze_top_factors_summary(results_df):
    """
    Analyze top factors across all votes using SHAP values
    """
    if results_df.empty:
        return
    
    print("\n" + "="*80)
    print("TOP FACTORS ANALYSIS (Based on SHAP Values)")
    print("="*80)
    
    for model in results_df['model'].unique():
        model_data = results_df[results_df['model'] == model]
        
        # Get weighted average importance (weighted by sample size)
        model_data['weighted_importance'] = model_data['importance_pct'] * model_data['sample_size']
        
        feature_stats = model_data.groupby('feature').agg({
            'weighted_importance': 'sum',
            'sample_size': 'sum',
            'importance_pct': 'mean',
            'mean_abs_shap_value': 'mean',
            'direction': lambda x: x.mode()[0] if not x.empty else 'neutral'
        })
        
        feature_stats['weighted_avg_importance'] = feature_stats['weighted_importance'] / feature_stats['sample_size']
        feature_stats = feature_stats.sort_values('weighted_avg_importance', ascending=False).head(15)
        
        print(f"\n{model} - Top 15 Features by Weighted Average Importance:")
        print("-" * 70)
        print(f"{'Feature':<40} {'Avg Importance':>15} {'Direction':>12}")
        print("-" * 70)
        for feature, row in feature_stats.iterrows():
            print(f"{feature:<40} {row['weighted_avg_importance']:>14.2f}% {row['direction']:>12}")
    
    # Analyze consistency of factors
    print("\n" + "="*80)
    print("FACTOR CONSISTENCY ANALYSIS")
    print("="*80)
    
    # Find factors that are consistently important
    for model in results_df['model'].unique():
        model_data = results_df[results_df['model'] == model]
        
        # Count how often each feature appears in top 10
        top_10_counts = {}
        unique_votes = model_data[['congress', 'session', 'chamber', 'roll_call_number']].drop_duplicates()
        
        for _, vote in unique_votes.iterrows():
            vote_data = model_data[
                (model_data['congress'] == vote['congress']) &
                (model_data['session'] == vote['session']) &
                (model_data['chamber'] == vote['chamber']) &
                (model_data['roll_call_number'] == vote['roll_call_number'])
            ].head(10)
            
            for feature in vote_data['feature']:
                top_10_counts[feature] = top_10_counts.get(feature, 0) + 1
        
        total_votes = len(unique_votes)
        consistency_df = pd.DataFrame([
            {'feature': k, 'appearances': v, 'consistency_pct': (v/total_votes)*100}
            for k, v in top_10_counts.items()
        ]).sort_values('consistency_pct', ascending=False).head(10)
        
        print(f"\n{model} - Most Consistent Top-10 Features:")
        print("-" * 60)
        for _, row in consistency_df.iterrows():
            print(f"{row['feature']:40s} appears in {row['consistency_pct']:5.1f}% of votes")

def main():
    # Load data
    print("Loading data...")
    df = pd.read_csv('rollcall_data.csv')
    
    print(f"Total records: {len(df)}")
    print(f"Unique lawmakers: {df['person_id'].nunique()}")
    print(f"Unique roll calls: {df['RollCallNumber'].nunique()}")
    
    # Analyze votes with SHAP
    print("\nAnalyzing roll call votes with SHAP values...")
    results, shap_data = analyze_rollcall_votes(df, save_shap_values=False)
    
    if not results.empty:
        # Save results
        results.to_csv('feature_importance_results_shap.csv', index=False)
        print(f"\nResults saved to 'feature_importance_results_shap.csv'")
        
        # Analyze top factors
        analyze_top_factors_summary(results)
        
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
                sample_size = model_results['sample_size'].iloc[0]
                yes_votes = model_results['yes_votes'].iloc[0]
                no_votes = model_results['no_votes'].iloc[0]
                
                print(f"\n{model_name} (Accuracy: {accuracy:.2%}, Sample: {sample_size}, Yes: {yes_votes}, No: {no_votes})")
                print("-" * 70)
                print(f"{'Feature':<40} {'Importance':>12} {'SHAP':>10} {'Direction':>10}")
                print("-" * 70)
                for _, row in model_results.iterrows():
                    print(f"{row['feature']:<40} {row['importance_pct']:>11.2f}% {row['mean_abs_shap_value']:>10.4f} {row['direction']:>10}")
        
        # Summary statistics
        print("\n" + "="*80)
        print("MODEL PERFORMANCE SUMMARY")
        print("="*80)
        
        for model in results['model'].unique():
            model_data = results[results['model'] == model]
            unique_votes = model_data[['congress', 'session', 'chamber', 'roll_call_number']].drop_duplicates()
            
            accuracies = []
            for _, vote in unique_votes.iterrows():
                vote_accuracy = model_data[
                    (model_data['congress'] == vote['congress']) &
                    (model_data['session'] == vote['session']) &
                    (model_data['chamber'] == vote['chamber']) &
                    (model_data['roll_call_number'] == vote['roll_call_number'])
                ]['model_accuracy'].iloc[0]
                accuracies.append(vote_accuracy)
            
            accuracies = np.array(accuracies)
            print(f"\n{model}:")
            print(f"  Mean Accuracy: {accuracies.mean():.2%}")
            print(f"  Std Deviation: {accuracies.std():.2%}")
            print(f"  Number of votes analyzed: {len(accuracies)}")
    else:
        print("No results generated. Please check the data.")

if __name__ == "__main__":
    main()