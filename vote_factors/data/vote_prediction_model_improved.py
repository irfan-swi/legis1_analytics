import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
from sklearn.feature_selection import SelectKBest, f_classif
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

def create_interaction_features(df):
    """
    Create interaction features between key variables
    """
    # Party-Region interaction
    df['party_region'] = df['party'] + '_' + df['region']
    
    # Party-Cosponsorship interaction
    df['party_cosponsor'] = df['party'] + '_' + df['cosponsorship_status'].astype(str)
    
    # Experience ratio (staffer vs regular experience)
    df['experience_ratio'] = np.where(
        df['years_of_experience'] > 0,
        df['years_of_staffer_experience'] / (df['years_of_experience'] + 1),
        0
    )
    
    # Seniority category
    df['seniority'] = pd.cut(df['years_of_experience'], 
                             bins=[0, 2, 6, 12, 100], 
                             labels=['Freshman', 'Junior', 'Mid', 'Senior'])
    
    return df

def preprocess_data(df, include_interactions=True):
    """
    Preprocess the congressional vote data with optional interaction features
    """
    # Create a copy
    df_processed = df.copy()
    
    # Map states to regions
    df_processed['region'] = df_processed['state'].map(STATE_TO_REGION)
    
    # Create interaction features if requested
    if include_interactions:
        df_processed = create_interaction_features(df_processed)
    
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
    
    if include_interactions:
        categorical_features.extend(['party_region', 'party_cosponsor', 'seniority'])
        numerical_features.append('experience_ratio')
    
    # One-hot encode categorical variables
    df_encoded = pd.get_dummies(df_processed, columns=categorical_features, prefix=categorical_features)
    
    # Get all feature columns after encoding
    feature_cols = [col for col in df_encoded.columns if any(
        col.startswith(f"{feat}_") for feat in categorical_features
    )] + numerical_features + binary_features
    
    # Remove any columns that don't exist
    feature_cols = [col for col in feature_cols if col in df_encoded.columns]
    
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
        
        # Calculate direction using permutation importance approach
        directions = []
        for i, feature in enumerate(feature_names):
            if X[:, i].std() > 0:  # Only for features with variation
                # Use correlation with target as proxy for direction
                correlation = np.corrcoef(X[:, i], y)[0, 1]
                direction = 1 if correlation > 0.01 else -1 if correlation < -0.01 else 0
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

def analyze_rollcall_votes(df, include_interactions=True, use_cv=False):
    """
    Analyze each roll call vote and generate feature importance
    """
    # Preprocess the data
    df_processed, feature_cols = preprocess_data(df, include_interactions)
    
    # Get unique roll call votes (including chamber)
    unique_votes = df_processed[['RollCallNumber', 'session', 'congress', 'chamber']].drop_duplicates()
    
    # Initialize results storage
    all_results = []
    
    # Initialize models with regularization
    models = {
        'LogisticRegression': LogisticRegression(
            max_iter=1000, 
            random_state=42,
            penalty='l2',
            C=1.0,  # Regularization strength
            solver='liblinear'
        ),
        'RandomForest': RandomForestClassifier(
            n_estimators=100, 
            random_state=42, 
            max_depth=8,  # Reduced from 10 to prevent overfitting
            min_samples_split=5,
            min_samples_leaf=3,
            max_features='sqrt'
        ),
        'XGBoost': XGBClassifier(
            n_estimators=100, 
            random_state=42, 
            max_depth=4,  # Reduced from 5
            min_child_weight=3,
            gamma=0.1,  # Add minimum loss reduction
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,  # L1 regularization
            reg_lambda=1.0,  # L2 regularization
            use_label_encoder=False, 
            eval_metric='logloss'
        )
    }
    
    print(f"Analyzing {len(unique_votes)} unique roll call votes...")
    if include_interactions:
        print("Including interaction features...")
    
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
        
        # Check if vote has both classes
        unique_votes_in_data = vote_data['vote_binary'].unique()
        if len(unique_votes_in_data) < 2:
            print(f"Skipping vote {roll_call} - only one class present")
            continue
            
        # Prepare features and target
        X = vote_data[feature_cols].values
        y = vote_data['vote_binary'].values
        
        # Handle missing values
        X = np.nan_to_num(X, nan=0)
        
        # Standardize numerical features
        scaler = StandardScaler()
        numerical_indices = []
        for feat in ['age', 'years_of_experience', 'years_of_staffer_experience', 
                    'staffer_turnover_rate', 'experience_ratio']:
            if feat in feature_cols:
                numerical_indices.append(feature_cols.index(feat))
        
        X_scaled = X.copy()
        if numerical_indices:
            X_scaled[:, numerical_indices] = scaler.fit_transform(X[:, numerical_indices])
        
        # Train each model and get feature importance
        for model_name, model in models.items():
            try:
                # Train model
                if use_cv and len(vote_data) > 50:
                    # Use cross-validation for larger samples
                    cv_scores = cross_val_score(model, X_scaled, y, cv=3, scoring='accuracy')
                    accuracy = cv_scores.mean()
                    model.fit(X_scaled, y)  # Still fit on full data for importance
                else:
                    model.fit(X_scaled, y)
                    y_pred = model.predict(X_scaled)
                    accuracy = accuracy_score(y, y_pred)
                
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
                importance_df['model_accuracy'] = accuracy
                
                # Add sample size for transparency
                importance_df['sample_size'] = len(vote_data)
                importance_df['yes_votes'] = (y == 1).sum()
                importance_df['no_votes'] = (y == 0).sum()
                
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

def analyze_model_performance(results_df):
    """
    Analyze and report on model performance metrics
    """
    if results_df.empty:
        return
    
    print("\n" + "="*80)
    print("MODEL PERFORMANCE ANALYSIS")
    print("="*80)
    
    # Group by model
    for model in results_df['model'].unique():
        model_data = results_df[results_df['model'] == model]
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
        print(f"  Min Accuracy: {accuracies.min():.2%}")
        print(f"  Max Accuracy: {accuracies.max():.2%}")
        print(f"  Votes with >95% accuracy: {(accuracies > 0.95).sum()} ({(accuracies > 0.95).mean():.1%})")
        print(f"  Votes with >90% accuracy: {(accuracies > 0.90).sum()} ({(accuracies > 0.90).mean():.1%})")
    
    # Identify most important features across all votes
    print("\n" + "="*80)
    print("TOP FEATURES ACROSS ALL VOTES")
    print("="*80)
    
    for model in results_df['model'].unique():
        model_data = results_df[results_df['model'] == model]
        
        # Get average importance for each feature
        feature_importance = model_data.groupby('feature')['importance_pct'].agg(['mean', 'std', 'count'])
        feature_importance = feature_importance[feature_importance['count'] > 10]  # Filter rare features
        feature_importance = feature_importance.sort_values('mean', ascending=False).head(10)
        
        print(f"\n{model} - Top 10 Features by Average Importance:")
        print("-" * 60)
        for feature, row in feature_importance.iterrows():
            print(f"  {feature:40s} {row['mean']:6.2f}% (±{row['std']:5.2f}%)")

def main():
    # Load data
    print("Loading data...")
    df = pd.read_csv('rollcall_data.csv')
    
    print(f"Total records: {len(df)}")
    print(f"Unique lawmakers: {df['person_id'].nunique()}")
    print(f"Unique roll calls: {df['RollCallNumber'].nunique()}")
    
    # Analyze votes with interaction features
    print("\nAnalyzing roll call votes with improved models...")
    results = analyze_rollcall_votes(df, include_interactions=True, use_cv=False)
    
    if not results.empty:
        # Save results
        results.to_csv('feature_importance_results_improved.csv', index=False)
        print(f"\nResults saved to 'feature_importance_results_improved.csv'")
        
        # Analyze model performance
        analyze_model_performance(results)
        
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
                print("-" * 60)
                for _, row in model_results.iterrows():
                    print(f"{row['feature']:40s} {row['importance_pct']:6.2f}% ({row['direction']})")
    else:
        print("No results generated. Please check the data.")

if __name__ == "__main__":
    main()