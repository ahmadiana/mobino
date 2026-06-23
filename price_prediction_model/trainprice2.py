import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

# 1. Load Data
df = pd.read_csv("train_price_dataset_1.csv")

# ==========================================
# FINAL CHOSEN FEATURES (All 3 scores included)
# ==========================================
feature_columns = [
    "Storage", 
    "RAM", 
    "DollarRate", 
    "LaunchMSRP", 
    "age", 
    "market_tier_bracket",
    "chipset_score",
    "score_camera_system",
    "score_display"
]

CATEGORICAL_FEATURES = ["market_tier_bracket"]

# 2. Clean features and drop duplicate spec combinations
df_unique = df.groupby(feature_columns)["price_toman"].mean().reset_index()

for col in CATEGORICAL_FEATURES:
    if col in df_unique.columns:
        df_unique[col] = df_unique[col].astype(str)

X = df_unique[feature_columns]
y = df_unique["price_toman"]

print(f"✅ Final model configuration:")
print(f"   Total unique phone configurations: {len(X)}")
print(f"   Training on {len(feature_columns)} features")
print(f"   Categorical features: {CATEGORICAL_FEATURES}\n")

# 3. Split into Train (80%) and Test (20%) sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42
)

print(f"Training with: {len(X_train)} unique rows")
print(f"Testing with: {len(X_test)} completely unseen rows\n")

# 4. Train the Model
cb_params = {
    "iterations": 800,
    "learning_rate": 0.04,
    "depth": 5,
    "l2_leaf_reg": 5,
    "verbose": 0,
}
model = CatBoostRegressor(**cb_params)
model.fit(X_train, y_train, cat_features=CATEGORICAL_FEATURES)

# 5. Evaluate
predictions = model.predict(X_test)
mae = mean_absolute_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

print("=" * 60)
print("📊 FINAL MODEL PERFORMANCE")
print("=" * 60)
print(f"Mean Absolute Error (MAE): {mae:>12,.0f} Toman")
print(f"R² Score:                  {r2:.4f}")
print("=" * 60)

# 6. Sample predictions
results = pd.DataFrame({
    "Actual Price": y_test, 
    "Predicted Price": predictions
}).reset_index(drop=True)

print("\n--- Sample Predictions vs Actuals ---")
print(results.head(10).round(0))

# 7. Retrain on 100% of data and save
print("\n" + "=" * 60)
print("🚀 Training FINAL model on 100% of data...")
print("=" * 60)

final_model = CatBoostRegressor(**cb_params)
final_model.fit(X, y, cat_features=CATEGORICAL_FEATURES)
final_model.save_model("phone_price_model.cbm")
print("✅ Model exported as 'phone_price_model.cbm'!")

# 8. Feature importance
print("\n=== Feature Importance ===")
feature_importance = final_model.get_feature_importance()
importance_df = pd.DataFrame({
    'Feature': feature_columns,
    'Importance': feature_importance
}).sort_values('Importance', ascending=False)

print(importance_df.to_string(index=False))

# 9. Save feature list for inference
with open("model_features.txt", "w") as f:
    f.write(",".join(feature_columns))
print(f"\n✅ Feature list saved to 'model_features.txt'")