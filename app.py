from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
import re

# Import your pipeline modules
from scraper import run_scraper_pipeline
from clean_mapper import run_production_mapping
from ml_predictor import predict_phone_scores
from gemini_msrp import get_launch_msrp_prices
from gemini_review import get_ai_review
from price_predictor import predict_phone_prices
from dollar_rate import fetch_and_cache_dollar_rate, get_cached_dollar_rate

app = FastAPI(title="Mobino Core Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LinkPayload(BaseModel):
    urls: List[str]

class AnalyzePayload(BaseModel):
    # The frontend calls /api/scrape first, gets raw_scraped_data back, then
    # sends it straight into /api/analyze for the rest of the pipeline. This
    # lets the UI show a distinct "scraping" loading state vs an "analyzing"
    # loading state, since these are now two separate HTTP round trips.
    raw_scraped_data: dict


def strip_capacity_tokens(name: str) -> str:
    """
    Scraped product names/titles often include the specific storage/RAM
    variant the user is viewing, e.g. 'Galaxy S24 Ultra 256/12 گیگابایت' or
    'iPhone 15 Pro Max 256GB'. If we send that as-is to Gemini, it will price
    THAT specific SKU instead of the base/lowest-storage variant, even though
    our prompt asks for the base variant -- the explicit capacity in the name
    overrides the instruction. This strips those tokens so Gemini sees a
    clean model name and correctly applies its own base-variant logic.
    """
    cleaned = name
    # Persian patterns: '256/12 گیگابایت', '256 گیگابایت', '12 گیگ رم'
    cleaned = re.sub(r'\d+\s*/\s*\d+\s*(گیگابایت|گیگ)?', '', cleaned)
    cleaned = re.sub(r'\d+\s*(گیگابایتی|گیگابایت|گیگ)\s*(رم)?', '', cleaned)
    # English patterns: '256GB', '12GB', '256/12GB', '256 GB', '12 GB RAM'
    cleaned = re.sub(r'\d+\s*/\s*\d+\s*GB', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\d+\s*GB(\s*RAM)?', '', cleaned, flags=re.IGNORECASE)
    # collapse extra whitespace/punctuation left behind
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' -،,')
    return cleaned or name  # never return an empty string


@app.on_event("startup")
def on_startup():
    # Fetch the live USD/Toman rate ONCE when the server boots, and keep it
    # cached in memory for every request -- per your instructions, we do not
    # want to re-scrape tgju.org on every /api/analyze call.
    print("[app.py] server starting up -- fetching live USD/Toman exchange rate ...")
    fetch_and_cache_dollar_rate()

@app.get("/")
async def read_index():
    return FileResponse('index.html')

@app.get("/docs.html")
async def read_docs():
    return FileResponse('docs.html')

@app.get("/favicon.svg")
async def serve_favicon():
    return FileResponse('favicon.svg')

@app.post("/api/scrape")
def scrape_links(payload: LinkPayload):
    """
    PHASE 1: scraping only. The frontend calls this first, shows its
    persistent 'در حال دریافت اطلاعات محصولات...' notification while this
    is running, then -- as soon as this returns -- switches to the
    full-screen 'در حال تحلیل اطلاعات' overlay and immediately calls
    /api/analyze with the raw_scraped_data this endpoint returns.
    """
    if not payload.urls:
        raise HTTPException(status_code=400, detail="لینک‌های ارسالی نمی‌توانند خالی باشند.")

    try:
        print(f"\n{'='*70}")
        print(f"📥 [app.py] /api/scrape called with {len(payload.urls)} link(s):")
        for u in payload.urls:
            print(f"     - {u}")
        print(f"{'='*70}")

        print("\n[app.py] (scrape phase) calling run_scraper_pipeline() ...")
        raw_scraped_data = run_scraper_pipeline(payload.urls)
        print(f"[app.py] (scrape phase) done. Got {len(raw_scraped_data)} raw item(s) back from scraper.py")

        return {
            "success": True,
            "raw_scraped_data": raw_scraped_data,
        }

    except Exception as server_error:
        import traceback
        print(f"❌ [app.py] Scraping phase failure: {str(server_error)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="خطایی در فرآیند دریافت اطلاعات محصولات رخ داده است.")


@app.post("/api/analyze")
def analyze_links(payload: AnalyzePayload):
    """
    PHASE 2: mapping, scoring, Gemini MSRP lookup, price prediction, and
    the Gemini review -- everything EXCEPT scraping, which already
    happened in /api/scrape. The frontend keeps the full-screen
    'در حال تحلیل اطلاعات' overlay up for this entire call.
    """
    raw_scraped_data = payload.raw_scraped_data
    if not raw_scraped_data:
        raise HTTPException(status_code=400, detail="داده‌های اسکرپ‌شده ارسالی نمی‌توانند خالی باشند.")

    try:
        print(f"\n{'='*70}")
        print(f"📥 [app.py] /api/analyze called with {len(raw_scraped_data)} pre-scraped item(s)")
        print(f"{'='*70}")

        # Step 1: Map raw specifications into clean structural data frames
        print("\n[app.py] STEP 1/6: calling run_production_mapping() ...")
        df_mapped_features = run_production_mapping(raw_scraped_data)
        print(f"[app.py] STEP 1/6 done. Mapped DataFrame shape: {df_mapped_features.shape}")

        # Step 2: Impute missing entries, reorder columns dynamically, and run the 6 CatBoost score models
        print("\n[app.py] STEP 2/6: calling predict_phone_scores() ...")
        calculated_scores_list = predict_phone_scores(df_mapped_features)
        print(f"[app.py] STEP 2/6 done. Got {len(calculated_scores_list)} scored record(s) back from ml_predictor.py")

        # Step 3: Ask Gemini for each phone's launch MSRP (USD), in the same
        # order as calculated_scores_list, then zip the results back onto
        # each record's _source_key (NOT by raw position, since downstream
        # consumers key off _source_key consistently).
        print("\n[app.py] STEP 3/6: calling get_launch_msrp_prices() (Gemini script 1) ...")
        ordered_source_keys = [r.get("_source_key") for r in calculated_scores_list]
        ordered_phone_names = []
        for k in ordered_source_keys:
            raw_name = raw_scraped_data.get(k, {}).get("product_name_en") or raw_scraped_data.get(k, {}).get("title", "Unknown Device")
            clean_name = strip_capacity_tokens(raw_name)
            if clean_name != raw_name:
                print(f"[app.py]   - stripped capacity tokens from phone name: '{raw_name}' -> '{clean_name}'")
            ordered_phone_names.append(clean_name)
        ordered_msrp_prices = get_launch_msrp_prices(ordered_phone_names)
        launch_msrp_by_key = dict(zip(ordered_source_keys, ordered_msrp_prices))
        print(f"[app.py] STEP 3/6 done. LaunchMSRP by source_key: {launch_msrp_by_key}")

        # Step 4: Run the price prediction model (Toman), using the cached
        # DollarRate, the just-fetched LaunchMSRP values, and the relevant
        # fields already present on each scored record.
        print("\n[app.py] STEP 4/6: calling predict_phone_prices() ...")
        dollar_rate = get_cached_dollar_rate()
        predicted_price_by_key = predict_phone_prices(calculated_scores_list, launch_msrp_by_key, dollar_rate)
        print(f"[app.py] STEP 4/6 done. predicted price_toman by source_key: {predicted_price_by_key}")

        # Step 5: Merge raw scraper fields (image_url, price, Persian name),
        # LaunchMSRP, and predicted_price_toman back onto each scored record
        # using _source_key, since ml_predictor.py sorts rows by score_overall
        # and positional merging would attach the wrong image/price.
        print("\n[app.py] STEP 5/6: merging raw scraper fields + MSRP + predicted price onto scored records ...")
        enriched_predictions = []
        for record in calculated_scores_list:
            source_key = record.get("_source_key")
            raw_item = raw_scraped_data.get(source_key, {}) if source_key else {}

            merged = dict(record)
            merged["product_name_fa"] = raw_item.get("product_name_fa") or raw_item.get("title", "")
            merged["image_url"] = raw_item.get("image_url", "")
            merged["price"] = raw_item.get("price", "")  # current Digikala price (قیمت دیجی‌کالا)
            merged["url"] = raw_item.get("url", "")
            merged["launch_msrp_usd"] = launch_msrp_by_key.get(source_key, 0)
            merged["predicted_price_toman"] = predicted_price_by_key.get(source_key)  # قیمت پیش‌بینی شده
            
            # 👇 ADD THIS LINE TO PASS THE FLAG TO THE FRONTEND 👇
            merged["is_out_of_stock"] = raw_item.get("is_out_of_stock", False)
            
            enriched_predictions.append(merged)

            print(f"[app.py]   - source_key='{source_key}' merged -> name='{merged['product_name_fa'][:30]}', "
                  f"digikala_price='{merged['price']}', predicted_price_toman={merged['predicted_price_toman']}, "
                  f"score_overall={merged.get('score_overall')}")

        # Step 6: Ask Gemini for the Persian review/comparison, passing the
        # untouched raw Digikala scrape for each phone (full item: title,
        # specifications, price, image, etc.) -- NOT the mapped/cleaned specs,
        # since that's redundant and the raw scrape has more detail anyway.
        print("\n[app.py] STEP 6/6: calling get_ai_review() (Gemini script 2) ...")
        review_payload = []
        for merged in enriched_predictions:
            source_key = merged.get("_source_key")
            raw_item = raw_scraped_data.get(source_key, {})
            review_payload.append({
                "name": merged.get("product_name_fa") or merged.get("product_name", "Unknown Device"),
                "raw_digikala_data": raw_item,
            })
        ai_review = get_ai_review(review_payload)
        print(f"[app.py] STEP 6/6 done. AI review covers {len(ai_review.get('phones', []))} phone(s)")

        print("\n✅ [app.py] Full analysis pipeline completed successfully. Returning to frontend.")
        print(f"{'='*70}\n")

        return {
            "success": True,
            "data": raw_scraped_data,
            "predictions": enriched_predictions,
            "ai_review": ai_review,
            "dollar_rate": dollar_rate,
        }
        
    except FileNotFoundError as fnf_err:
        print(f"❌ [app.py] Structural Deployment Failure: {str(fnf_err)}")
        raise HTTPException(status_code=500, detail="فایل‌های مدل هوش مصنوعی یا مستندات بر روی سرور یافت نشد.")
    except Exception as server_error:
        import traceback
        print(f"❌ [app.py] System processing failure: {str(server_error)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="خطایی در فرآیند تحلیل هوشمند رخ داده است.")


# Serves anything placed in a local "static" folder (e.g. images, CSS, extra
# JS files) at /static/<filename>, without needing a new @app.get route for
# every single asset. NOTE: this is intentionally NOT mounted at "/", since
# that would expose your whole project directory (including config.py and
# its API keys) as downloadable static files. index.html and docs.html keep
# their own explicit routes above for that reason -- add new top-level HTML
# pages the same way, with their own @app.get(...) route.
import os
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")