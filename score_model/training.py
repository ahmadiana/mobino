import os
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# --- 1. Load Dataset ---
file_path = "review_model_dataset.csv"
df = pd.read_csv(file_path)  # Changed from read_excel to read_csv

# --- 2. Define Architecture ---
# The 6 specific dimensions we want to predict
TARGETS = [
    "score_performance_hardware",
    "score_camera_system",
    "score_display",
    "score_design_build_quality",
    "score_battery_charging",
    "score_software_os_connectivity_features"
]

# Columns to completely hide from the AI
DROP_COLUMNS = [
    "product_name", 
    "score_overall", # Calculated later mathematically
    "chipset"        # Dropped in favor of chipset_score to prevent OOV errors
]

# Categorical features list (minus chipset)
CATEGORICAL_FEATURES = [
    "market_tier_bracket",
    "storage_type",
    "display_tech",
    "IP_Rating",
    "max_network_generation",
    "operating_system",
    "back_panel_material",
    "chassis_frame_material",
    "HDR_status",
    "display_protection_tier",
    "form_factor"
]

# --- 3. Clean and Prep the Master Feature Matrix (X) ---
# Remove all target columns and unnecessary metadata to form the base inputs
X_base = df.drop(columns=TARGETS + [col for col in DROP_COLUMNS if col in df.columns])

# Force categoricals to strings and fill NaNs (FIXED ORDER: fillna before astype)
for col in CATEGORICAL_FEATURES:
    if col in X_base.columns:
        X_base[col] = X_base[col].fillna("missing").astype(str)

print(f"Feature Matrix Shape: {X_base.shape}")
print(f"Number of Categoricals: {len(CATEGORICAL_FEATURES)}")

# --- 4. Training Loop for the 6 Specialized Models ---
models = {}

for target in TARGETS:
    print(f"\n{'='*50}")
    print(f"🚀 Training Model for: {target}")
    print(f"{'='*50}")
    
    # Isolate the specific target variable
    y = df[target]
    
    # Split the data (80/20)
    X_train, X_val, y_train, y_val = train_test_split(X_base, y, test_size=0.2, random_state=42)
    
    # Create optimized CatBoost Data Pools
    train_pool = Pool(X_train, y_train, cat_features=CATEGORICAL_FEATURES)
    val_pool = Pool(X_val, y_val, cat_features=CATEGORICAL_FEATURES)
    
    # Initialize the Regressor
    model = CatBoostRegressor(
        iterations=1000,
        learning_rate=0.05,
        depth=6,
        loss_function="RMSE",
        eval_metric="MAE",
        random_seed=42,
        early_stopping_rounds=50,
        verbose=200 # Keep console clean, print every 200 steps
    )
    
    # Train
    model.fit(train_pool, eval_set=val_pool, use_best_model=True)
    
    # Evaluate
    y_pred = model.predict(X_val)
    mae = mean_absolute_error(y_val, y_pred)
    r2 = r2_score(y_val, y_pred)
    print(f"\n✅ {target} Results -> MAE: {mae:.2f} | R2: {r2:.3f}")
    
    # Save the model to disk
    model_filename = f"model_{target}.cbm"
    model.save_model(model_filename)
    models[target] = model_filename

print("\n🎉 All 6 predictive models trained and saved successfully!")