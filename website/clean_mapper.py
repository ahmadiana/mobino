import re
import pandas as pd

# Import your existing functional micro-scripts
from script1 import parse_release_year
from script2 import parse_market_tier
from script3 import parse_ram_and_storage
from script4 import parse_display_specs
from script5 import parse_refresh_rate_and_brightness
from script6 import parse_weight_and_thickness
from script7 import parse_system_and_camera_specs
from script8 import parse_battery_and_charging_specs
from script9 import parse_camera_features
from script10 import parse_video_features
from script11 import parse_chipset
from script12 import parse_storage_and_display
from script13 import parse_protection_specs
from script14 import parse_body_materials
from script15 import parse_screen_features

def parse_form_factor(product_name_en, title):
    """
    SCRIPT 16: Scans the English product name to extract specialized 
    form factors, defaulting to standard 'Bar'.
    """
    # Safely look at English name first, fallback to fallback title if empty
    name_str = str(product_name_en if product_name_en else title or "").strip()
    
    fold_keywords = r"\b(fold|flip|trifold|flex|bendable|foldable)\b"
    brand_foldable_lines = r"\b(magic v|mate x|mix fold|phantom v|razr|open|find n|axon m)\b"
    combined_pattern = f"{fold_keywords}|{brand_foldable_lines}"
    
    match = re.search(combined_pattern, name_str, flags=re.IGNORECASE)
    if match:
        matched_text = match.group(0).lower()
        if "flip" in matched_text or "razr" in matched_text:
            return "Flip"
        elif "trifold" in matched_text:
            return "Trifold"
        else:
            return "Fold"
            
    return "Bar"

def run_production_mapping(scraped_data_dict):
    """
    Takes raw dictionary straight from scraper.py in memory,
    runs all 16 micro-scripts, and returns a clean Pandas DataFrame.
    """
    print(f"\n[clean_mapper] ===> run_production_mapping() called with {len(scraped_data_dict)} raw item(s)")

    # Convert dictionary values {"1": {...}, "2": {...}} to a clean iterable list
    # We keep the original dict key (e.g. "1", "2") as _source_key so we can
    # re-merge raw scraper fields (image_url, price, product_name_fa) back onto
    # this row later in app.py, even after ml_predictor.py re-sorts the rows.
    item_list = list(scraped_data_dict.items())
    processed_rows = []

    for source_key, item in item_list:
        if "error" in item:
            print(f"[clean_mapper]  - item '{source_key}' contains a scraper error, skipping: {item.get('error')}")
            continue

        specs_payload = item.get("specifications", {})
        print(f"[clean_mapper]  - mapping item '{source_key}': title='{str(item.get('title',''))[:40]}', spec categories={list(specs_payload.keys())[:5]}")
        
        # Build out clean structural row result matching model expectations
        row_result = {
            "_source_key": source_key,
            "product_name": item.get("title", "Unknown Device"),
        }
        
        # Execute scripts 1 through 15
        row_result["release_year"] = parse_release_year(specs_payload)
        row_result["market_tier_bracket"] = parse_market_tier(specs_payload)
        row_result["ram_gb"], row_result["storage_gb"] = parse_ram_and_storage(specs_payload)
        row_result["display_ppi"], row_result["display_size_inches"] = parse_display_specs(specs_payload)
        row_result["display_refresh_rate_hz"], row_result["brightness_nits"] = parse_refresh_rate_and_brightness(specs_payload)
        row_result["weight_grams"], row_result["thickness_mm"] = parse_weight_and_thickness(specs_payload)
        
        (
            row_result["rear_camera_count"], row_result["nano_sim"], row_result["has_esim_support"], 
            row_result["max_network_generation"], row_result["operating_system_version"], 
            row_result["front_camera_megapixels"], row_result["operating_system"]
        ) = parse_system_and_camera_specs(specs_payload)
        
        (
            row_result["battery_capacity_mah"], row_result["wired_charging_power"], 
            row_result["has_wireless_charging"]
        ) = parse_battery_and_charging_specs(specs_payload)
        
        (
            row_result["rear_main_camera_megapixels"], row_result["Aperture1"], row_result["has_optical_image_stabilization"], 
            row_result["has_periscope"], row_result["has_telephoto"], row_result["has_macro"], row_result["has_ultrawide"]
        ) = parse_camera_features(specs_payload)
        
        row_result["video_resolution_options"], row_result["fps"] = parse_video_features(specs_payload)
        row_result["chipset"], row_result["chipset_score"] = parse_chipset(specs_payload)
        row_result["storage_type"], row_result["display_tech"] = parse_storage_and_display(specs_payload)
        
        (
            row_result["is_dustproof"], row_result["is_waterproof"], row_result["IP_Rating"]
        ) = parse_protection_specs(specs_payload)
        
        row_result["back_panel_material"], row_result["chassis_frame_material"] = parse_body_materials(specs_payload)
        row_result["HDR_status"], row_result["display_protection_tier"] = parse_screen_features(specs_payload)

        # Execute SCRIPT 16 (Form Factor Extraction)
        row_result["form_factor"] = parse_form_factor(
            product_name_en=item.get("product_name_en", ""),
            title=item.get("title", "")
        )

        processed_rows.append(row_result)

    df_result = pd.DataFrame(processed_rows)
    print(f"[clean_mapper] <=== returning DataFrame with shape {df_result.shape} (rows, columns)")
    if not df_result.empty:
        print(f"[clean_mapper]      columns: {list(df_result.columns)}")
    # Return as a clean Pandas DataFrame in memory
    return df_result
