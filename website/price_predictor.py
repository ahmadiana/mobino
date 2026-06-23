"""
Price prediction (Toman) using a dedicated CatBoost model.

Unlike ml_predictor.py's 6 score models, this model has a small, fixed
feature schema (no dynamic CSV-blueprint matching needed), trained on:

    Storage, RAM, DollarRate, LaunchMSRP, age,
    chipset_score, score_camera_system, score_display, market_tier_bracket

Target: price_toman

market_tier_bracket here is Title-Case ("Entry-Level", "Mid-Range",
"Flagship") -- NOT the lowercase-hyphen form used by the 6 score models in
ml_predictor.py. This file converts internally so callers can keep passing
the lowercase form used everywhere else in the pipeline.
"""
import os
import pandas as pd
from catboost import CatBoostRegressor, Pool

PRICE_MODEL_FILE = "model_price_toman.cbm"

CATEGORICAL_FEATURES = ["market_tier_bracket"]

FEATURE_ORDER = [
    "Storage",
    "RAM",
    "DollarRate",
    "LaunchMSRP",
    "age",
    "chipset_score",
    "score_camera_system",
    "score_display",
    "market_tier_bracket",
]

# Maps the lowercase-hyphen tier names used elsewhere in the pipeline
# (ml_predictor.py / clean_mapper.py) to the Title-Case form this specific
# model was trained on.
TIER_NAME_TO_TITLE_CASE = {
    "entry-level": "Entry-Level",
    "mid-range": "Mid-Range",
    "flagship": "Flagship",
    "unknown": "Mid-Range",  # same fallback convention as ml_predictor.py
}

CURRENT_YEAR = 2026


def _to_title_case_tier(tier_value: str) -> str:
    key = str(tier_value).strip().lower()
    return TIER_NAME_TO_TITLE_CASE.get(key, "Mid-Range")


def predict_phone_prices(scored_records: list[dict], launch_msrp_by_key: dict, dollar_rate: float) -> dict:
    """
    scored_records: the list of dicts coming out of ml_predictor.predict_phone_scores()
        (after app.py's _source_key merge), each already containing
        storage_gb, ram_gb, release_year, chipset_score, score_camera_system,
        score_display, market_tier_bracket, and _source_key.

    launch_msrp_by_key: dict mapping _source_key -> LaunchMSRP (int, USD),
        as produced by gemini_msrp.get_launch_msrp_prices() and zipped back
        onto each phone's _source_key by app.py.

    dollar_rate: the cached DollarRate value (see dollar_rate.py).

    Returns: dict mapping _source_key -> predicted price_toman (float).
    On any failure (e.g. model file missing), returns an empty dict and logs
    the issue, so the rest of the pipeline can still complete.
    """
    print(f"\n[price_predictor] ===> predict_phone_prices() called for {len(scored_records)} phone(s), DollarRate={dollar_rate}")

    if not scored_records:
        return {}

    if not os.path.exists(PRICE_MODEL_FILE):
        print(f"[price_predictor] ❌ model file '{PRICE_MODEL_FILE}' not found in {os.getcwd()}. Skipping price prediction.")
        return {}

    rows = []
    source_keys = []

    for record in scored_records:
        source_key = record.get("_source_key")
        launch_msrp = launch_msrp_by_key.get(source_key, 0)
        release_year = record.get("release_year", CURRENT_YEAR)

        try:
            age = max(0, CURRENT_YEAR - int(release_year))
        except (TypeError, ValueError):
            age = 0

        row = {
            "Storage": record.get("storage_gb", 0.0),
            "RAM": record.get("ram_gb", 0.0),
            "DollarRate": dollar_rate,
            "LaunchMSRP": launch_msrp,
            "age": age,
            "chipset_score": record.get("chipset_score", 0.0),
            "score_camera_system": record.get("score_camera_system", 0.0),
            "score_display": record.get("score_display", 0.0),
            "market_tier_bracket": _to_title_case_tier(record.get("market_tier_bracket", "unknown")),
        }
        rows.append(row)
        source_keys.append(source_key)

        print(f"[price_predictor]  - source_key='{source_key}': {row}")

    X_inference = pd.DataFrame(rows)[FEATURE_ORDER].copy()

    for col in X_inference.columns:
        if col not in CATEGORICAL_FEATURES:
            X_inference[col] = pd.to_numeric(X_inference[col], errors="coerce").fillna(0.0)
        else:
            X_inference[col] = X_inference[col].astype(str)

    model = CatBoostRegressor()
    model.load_model(PRICE_MODEL_FILE)

    inference_pool = Pool(X_inference, cat_features=CATEGORICAL_FEATURES)
    predictions = model.predict(inference_pool)

    result = {}
    for source_key, predicted_price in zip(source_keys, predictions):
        result[source_key] = round(float(predicted_price), 0)

    print(f"[price_predictor] <=== predict_phone_prices() returning {len(result)} prediction(s): {result}")
    return result
