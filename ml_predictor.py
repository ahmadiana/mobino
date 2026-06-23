import os
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- 1. System Constants & Configurations ---
TARGETS = [
    "score_performance_hardware",
    "score_camera_system",
    "score_display",
    "score_design_build_quality",
    "score_battery_charging",
    "score_software_os_connectivity_features"
]

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

DROP_COLUMNS = ["product_name", "chipset", "score_overall"]

TIER_FALLBACKS = {
    "entry-level": {
        "chipset_score": 25,
        "storage_gb": 128.0,
        "ram_gb": 3.0,
        "display_size_inches": 6.5,
        "display_ppi": 260.0,
        "display_refresh_rate_hz": 60.0,
        "brightness_nits": 400.0,
        "battery_capacity_mah": 4000.0,
        "wired_charging_power": 10.0,
        "rear_main_camera_megapixels": 12.0,
        "front_camera_megapixels": 12.0,
        "weight_grams": 195.0,
        "thickness_mm": 8.9,
        "nano_sim": 1.0,
        "operating_system_version": 10.0,
        "rear_camera_count": 1.0,
        "fps": 30.0,
        "storage_type": "eMMC 5.1",
        "display_tech": "IPS LCD",
        "max_network_generation": "4G",
        "operating_system": "Android",
        "display_protection_tier": "none_generic",
        "has_wireless_charging": "FALSE",
        "has_esim_support": "FALSE",
        "has_ultrawide": "FALSE",
        "has_macro": "FALSE",
        "has_telephoto": "FALSE",
        "has_periscope": "FALSE",
        "has_optical_image_stabilization": "FALSE",
        "is_dustproof": "FALSE",
        "is_waterproof": "FALSE"
    },
    "mid-range": {
        "chipset_score": 50,
        "storage_gb": 128.0,
        "ram_gb": 6.0,
        "display_size_inches": 6.67,
        "display_ppi": 395.0,
        "display_refresh_rate_hz": 90.0,
        "brightness_nits": 800.0,
        "battery_capacity_mah": 5000.0,
        "wired_charging_power": 33.0,
        "rear_main_camera_megapixels": 50.0,
        "front_camera_megapixels": 16.0,
        "weight_grams": 185.0,
        "thickness_mm": 8.0,
        "nano_sim": 2.0,
        "operating_system_version": 13.0,
        "rear_camera_count": 2.0,
        "fps": 60.0,
        "display_tech": "AMOLED",
        "max_network_generation": "5G",
        "operating_system": "Android",
        "display_protection_tier": "standard_branded",
        "has_wireless_charging": "FALSE",
        "has_esim_support": "FALSE",
        "has_ultrawide": "TRUE",
        "has_macro": "TRUE",
        "has_telephoto": "FALSE",
        "has_periscope": "FALSE",
        "has_optical_image_stabilization": "FALSE",
        "is_dustproof": "TRUE",
        "is_waterproof": "FALSE"
    },
    "flagship": {
        "chipset_score": 75,
        "storage_gb": 256.0,
        "ram_gb": 12.0,
        "display_size_inches": 6.7,
        "display_ppi": 460.0,
        "display_refresh_rate_hz": 120.0,
        "brightness_nits": 1500.0,
        "battery_capacity_mah": 5000.0,
        "wired_charging_power": 67.0,
        "rear_main_camera_megapixels": 50.0,
        "front_camera_megapixels": 32.0,
        "weight_grams": 200.0,
        "thickness_mm": 7.8,
        "nano_sim": 2.0,
        "operating_system_version": 14.0,
        "rear_camera_count": 3.0,
        "fps": 60.0,
        "display_tech": "LTPO AMOLED",
        "max_network_generation": "5G",
        "operating_system": "Android",
        "display_protection_tier": "premium_branded",
        "has_wireless_charging": "TRUE",
        "has_esim_support": "TRUE",
        "has_ultrawide": "TRUE",
        "has_macro": "FALSE",
        "has_telephoto": "TRUE",
        "has_periscope": "FALSE",
        "has_optical_image_stabilization": "TRUE",
        "is_dustproof": "TRUE",
        "is_waterproof": "TRUE"
    }
}
TIER_FALLBACKS["unknown"] = TIER_FALLBACKS["mid-range"]

def handle_missing_specs(df_input):
    print(f"[ml_predictor] handle_missing_specs() called on DataFrame shape={df_input.shape}")
    df = df_input.copy()
    if "market_tier_bracket" in df.columns:
        df["market_tier_bracket"] = df["market_tier_bracket"].astype(str).str.strip().str.lower()
    else:
        print("[ml_predictor]  - 'market_tier_bracket' column missing entirely, defaulting all rows to 'unknown'")
        df["market_tier_bracket"] = "unknown"

    tier_counts = df["market_tier_bracket"].value_counts().to_dict()
    print(f"[ml_predictor]  - market tier distribution: {tier_counts}")

    for index, row in df.iterrows():
        tier = row["market_tier_bracket"]
        if tier not in TIER_FALLBACKS:
            print(f"[ml_predictor]  - row {index}: unrecognized tier '{tier}', falling back to 'unknown' defaults")
            tier = "unknown"

        tier_defaults = TIER_FALLBACKS[tier]
        for col in tier_defaults.keys():
            if col in df.columns:
                val = str(df.at[index, col]).strip().lower()
                if pd.isna(df.at[index, col]) or val in ["none", "", "nan", "unknown"]:
                    df.at[index, col] = tier_defaults[col]
            else:
                df.at[index, col] = tier_defaults[col]
    print(f"[ml_predictor] handle_missing_specs() done. Output shape={df.shape}")
    return df

def predict_phone_scores(df_mapped_input):
    print(f"\n[ml_predictor] ===> predict_phone_scores() called with DataFrame shape={df_mapped_input.shape}")
    if df_mapped_input.empty:
        print("[ml_predictor]  - input DataFrame is empty, returning [] immediately")
        return []

    # 1. Apply Tier-Specific Data Imputation
    cleaned_df = handle_missing_specs(df_mapped_input)

    # 2. Dynamic Column Matching using the CSV blueprint
    TRAIN_DATASET = "review_model_dataset.csv"
    if not os.path.exists(TRAIN_DATASET):
        print(f"[ml_predictor] ❌ blueprint file '{TRAIN_DATASET}' not found in {os.getcwd()}")
        raise FileNotFoundError(f"Cannot find master dataset blueprint tracking file: '{TRAIN_DATASET}'")

    df_train_blueprint = pd.read_csv(TRAIN_DATASET)
    expected_features = [col for col in df_train_blueprint.columns if col not in (TARGETS + DROP_COLUMNS)]
    print(f"[ml_predictor]  - blueprint expects {len(expected_features)} feature columns")

    missing_from_input = [c for c in expected_features if c not in cleaned_df.columns]
    if missing_from_input:
        print(f"[ml_predictor]  ⚠️ {len(missing_from_input)} expected feature(s) NOT produced by clean_mapper.py, will be filled with placeholder values: {missing_from_input}")

    for col in expected_features:
        if col not in cleaned_df.columns:
            cleaned_df[col] = "unknown" if col in CATEGORICAL_FEATURES else 0.0

    # Force strict alignment sequence matching the training data layout
    X_inference = cleaned_df[expected_features].copy()
    print(f"[ml_predictor]  - X_inference assembled with shape {X_inference.shape}")

    # --- NEW: BOOTSTRAP SANITIZER FOR NUMERIC/BOOLEAN FLAGS ---
    for col in X_inference.columns:
        if col not in CATEGORICAL_FEATURES:
            # If pandas read it as a standard boolean, convert to 1.0 / 0.0
            if X_inference[col].dtype == bool:
                X_inference[col] = X_inference[col].astype(float)
            # If it contains string versions of boolean variables, map them out explicitly
            elif X_inference[col].dtype == object or X_inference[col].dtype == str:
                # Standardize strings to uppercase to handle 'True', 'true', or 'TRUE' safely
                str_normalized = X_inference[col].astype(str).str.strip().str.upper()
                X_inference[col] = str_normalized.replace({
                    "TRUE": 1.0, "FALSE": 0.0, 
                    "YES": 1.0, "NO": 0.0, 
                    "NAN": 0.0, "UNKNOWN": 0.0, "": 0.0
                })
            
            # Enforce numerical data casting for CatBoost
            X_inference[col] = pd.to_numeric(X_inference[col], errors='coerce').fillna(0.0)

    # Synchronize categorical columns type formatting to strings strings
    for col in CATEGORICAL_FEATURES:
        if col in X_inference.columns:
            X_inference[col] = X_inference[col].astype(str)

    # 3. Predict Sub-Scores Using CatBoost
    scored_df = cleaned_df.copy()
    inference_pool = Pool(X_inference, cat_features=CATEGORICAL_FEATURES)

    for target in TARGETS:
        model_file = f"model_{target}.cbm"
        if not os.path.exists(model_file):
            print(f"[ml_predictor] ⚠️ Warning: {model_file} not found in {os.getcwd()}. Defaulting score entry to median (50.0).")
            scored_df[target] = 50.0
            continue
            
        model = CatBoostRegressor()
        model.load_model(model_file)
        scored_df[target] = model.predict(inference_pool)
        scored_df[target] = scored_df[target].clip(0.0, 100.0).round(2)
        print(f"[ml_predictor]  - {target}: predicted, sample values={scored_df[target].head(3).tolist()}")

    # 4. Formulate Overall Synthesized Quality Score
    scored_df["score_overall"] = (
        (scored_df["score_performance_hardware"] * 0.25) +
        (scored_df["score_camera_system"] * 0.20) +
        (scored_df["score_display"] * 0.20) +
        (scored_df["score_battery_charging"] * 0.15) +
        (scored_df["score_design_build_quality"] * 0.10) +
        (scored_df["score_software_os_connectivity_features"] * 0.10)
    )
    scored_df["score_overall"] = scored_df["score_overall"].round(2)

    # Sort results with the highest score first
    scored_df = scored_df.sort_values(by="score_overall", ascending=False)

    result_records = scored_df.to_dict(orient="records")
    print(f"[ml_predictor] <=== predict_phone_scores() returning {len(result_records)} record(s)")
    return result_records