library(tidyverse)
library(xgboost)
library(caret)
library(glmnet)
library(vip)        # Variable importance plots
library(pdp)        # Partial dependence plots
library(DALEX)      # Model explanations
library(pROC)       # ROC curves
library(corrplot)   # Correlation plots
library(scales)   



# Read the data
df <- read.csv("vote_214.csv")
#df <- read.csv("sample_vote.csv")

# Display initial data structure
cat("Dataset dimensions:", dim(df), "\n")
cat("Vote distribution:\n")
table(df$vote)

# Prepare the dataset
df_clean <- df %>%
  dplyr::select(-congress, -RollCallNumber, -display_name) %>%
  mutate(
    # Encode categorical variables
    party_republican = ifelse(party_name == "Republican", 1, 0),
    party_democrat = ifelse(party_name == "Democrat", 1, 0),
    gender_male = ifelse(gender == "M", 1, 0),
    gender_female = ifelse(gender == "F", 1,0),
    
    # Convert religion and race to factors for proper handling
    religion_id = as.factor(religion_id),
    race_id = as.factor(race_id),
    
    # Keep vote as numeric for modeling
    vote = as.numeric(vote)
  )

# One-hot encode state (optional - creates many features)
# Uncomment if you want state-level effects
# state_dummies <- model.matrix(~ us_state_id - 1, data = df_clean)
# df_clean <- cbind(df_clean, state_dummies)

# For now, let's create regional variables instead of individual states
df_clean <- df_clean %>%
  mutate(
    region = case_when(
      us_state_id %in% c("ME", "NH", "VT", "MA", "RI", "CT", "NY", "NJ", "PA") ~ "Northeast",
      us_state_id %in% c("OH", "MI", "IN", "IL", "WI", "MN", "IA", "MO", "ND", "SD", "NE", "KS") ~ "Midwest",
      us_state_id %in% c("MD", "DE", "WV", "VA", "NC", "SC", "GA", "FL", "KY", "TN", "AL", "MS", "AR", "LA", "OK", "TX") ~ "South",
      TRUE ~ "West"
    )
  ) %>%
  mutate(
    region_midwest = ifelse(region == "Midwest", 1, 0),
    region_south = ifelse(region == "South", 1, 0),
    region_west = ifelse(region == "West", 1, 0)
    # Northeast is the reference category
  )

# Create interaction terms
df_clean <- df_clean %>%
  mutate(
    party_experience = party_republican * experience_full_years,
    party_staff_exp = party_republican * TotalStafferExperience,
    #age_experience = age * experience_full_years
  )

# Select features for modeling
feature_cols <- c("party_republican", "party_democrat", 
                  "experience_full_years", "TurnoverRate", "TotalStafferExperience",
                  "gender_male", #"age",
                  "region_midwest", "region_south", "region_west",
                  "party_experience", "party_staff_exp") #, "age_experience")

# For models that need numeric matrices
X <- as.matrix(df_clean[, feature_cols])
y <- df_clean$vote



cat("\n========== LOGISTIC REGRESSION ANALYSIS ==========\n")

# Standard logistic regression
logit_model <- glm(vote ~ party_republican + party_democrat + 
                     experience_full_years + TurnoverRate + TotalStafferExperience +
                     gender_male + #age + 
                     region_midwest + region_south + region_west +
                     party_experience + party_staff_exp, # + age_experience,
                   data = df_clean, 
                   family = binomial(link = "logit"))

# Model summary
summary(logit_model)

# Calculate standardized coefficients for comparison
# Standardize continuous predictors
df_std <- df_clean
continuous_vars <- c("experience_full_years", "TurnoverRate", "TotalStafferExperience") #, "age")
df_std[continuous_vars] <- scale(df_std[continuous_vars])

logit_std <- glm(vote ~ party_republican + party_democrat + 
                   experience_full_years + TurnoverRate + TotalStafferExperience +
                   gender_male + #age + 
                   region_midwest + region_south + region_west,
                 data = df_std, 
                 family = binomial(link = "logit"))

# Extract and display standardized coefficients
coef_df <- data.frame(
  Feature = names(coef(logit_std))[-1],  # Remove intercept
  Coefficient = coef(logit_std)[-1],
  Std_Coefficient = coef(logit_std)[-1],
  Odds_Ratio = exp(coef(logit_std)[-1]),
  P_Value = summary(logit_std)$coefficients[-1, 4]
) %>%
  arrange(desc(abs(Std_Coefficient)))

cat("\nStandardized Coefficients (Logistic Regression):\n")
print(coef_df, digits = 3)

# Calculate McFadden R-squared
null_model <- glm(vote ~ 1, data = df_clean, family = binomial)
mcfadden_r2 <- 1 - (logLik(logit_model) / logLik(null_model))
cat("\nMcFadden R-squared:", round(mcfadden_r2, 4), "\n")

# Predictions and accuracy
logit_pred_prob <- predict(logit_model, type = "response")
logit_pred <- ifelse(logit_pred_prob > 0.5, 1, 0)
logit_accuracy <- mean(logit_pred == df_clean$vote)
cat("Logistic Regression Accuracy:", round(logit_accuracy, 4), "\n")

# ROC and AUC
logit_roc <- roc(df_clean$vote, logit_pred_prob)
cat("Logistic Regression AUC:", round(auc(logit_roc), 4), "\n")

logit_imp_normalized <- abs(coef_df$Std_Coefficient) / sum(abs(coef_df$Std_Coefficient))

comparison_df <- data.frame(
  Feature = coef_df$Feature,
  Logistic_Importance = logit_imp_normalized * 100
) %>%
  left_join(
    data.frame(
      Feature = importance_matrix$Feature    ),
    by = "Feature"
  )

calculate_standardized_contributions <- function(model, data, feature_cols) {
  
  # Standardize the data
  data_std <- data
  continuous_vars <- c("experience_full_years", "TurnoverRate", 
                       "TotalStafferExperience", "age")
  
  # Only standardize continuous variables
  for(var in continuous_vars) {
    if(var %in% names(data_std)) {
      data_std[[var]] <- scale(data_std[[var]])[,1]
    }
  }
  
  # Refit model with standardized data
  formula_str <- paste("vote ~", paste(feature_cols, collapse = " + "))
  model_std <- glm(formula_str, data = data_std, family = binomial)
  
  # Get standardized coefficients (excluding intercept)
  std_coefs <- coef(model_std)[-1]
  
  # Calculate percentage contributions
  abs_coefs <- abs(std_coefs)
  total_importance <- sum(abs_coefs)
  
  pct_contribution <- (abs_coefs / total_importance) * 100
  
  # Create results dataframe
  results <- data.frame(
    Feature = names(pct_contribution),
    Std_Coefficient = std_coefs,
    Abs_Coefficient = abs_coefs,
    Pct_Contribution = pct_contribution,
    Direction = ifelse(std_coefs > 0, "Positive", "Negative")
  ) %>%
    arrange(desc(Pct_Contribution))
  
  return(results)
}

calculate_standardized_contributions(logit_model,df_std,feature_cols)