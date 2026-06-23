import json
import time
from playwright.sync_api import sync_playwright

# Keep TARGET_URLS here so your script can still run standalone if needed
TARGET_URLS = []

def scrape_digikala_product(page, url):
    print(f"\nScraping: {url}")
    product_data = {
        "title": "Unknown Title",
        "url": url,
        "product_name_fa": "",
        "product_name_en": "",
        "price": "",
        "image_url": "",
        "specifications": {}
    }
    
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    
    title_element = page.locator('h1[data-testid="pdp-title"]')
    if title_element.count() > 0:
        product_data["title"] = title_element.first.inner_text().strip()
        print(f"Loaded: {product_data['title'][:40]}...")

    # ===== SCROLLING (from old script) =====
    print("Scrolling down to force specifications to render...")
    for _ in range(12):
        page.mouse.wheel(0, 800)
        page.wait_for_timeout(400)
        if page.locator('text="مشخصات"').count() > 0 or page.locator('text="مشاهده بیشتر"').count() > 0:
            break

    page.wait_for_timeout(1500)

    # ===== CLICKING "See More" BUTTONS (from old script) =====
    print("Looking for 'See More' buttons...")
    max_clicks = 10
    clicks_performed = 0
    
    for _ in range(max_clicks):
        expand_buttons = page.locator('text="مشاهده بیشتر"')
        count = expand_buttons.count()
        
        if count == 0:
            break
            
        clicked = False
        for i in range(count):
            btn = expand_buttons.nth(i)
            if btn.is_visible():
                try:
                    btn.scroll_into_view_if_needed()
                    btn.click(force=True)
                    clicks_performed += 1
                    print(f"-> Clicked 'See More' button successfully. (Total: {clicks_performed})")
                    page.wait_for_timeout(1500) 
                    clicked = True
                    break 
                except Exception as e:
                    print(f"-> Could not click expand button {i+1}: {e}")
        
        if not clicked:
            break

    if clicks_performed > 0:
        print(f"-> Finished clicking {clicks_performed} buttons. Waiting for page to fully load...")
        page.wait_for_timeout(2000) 
    else:
        print("-> 'See More' buttons not visible or not found. Checking for pre-expanded data...")

    # ===== SPECIFICATION EXTRACTION (from old script) =====
    spec_boxes = page.locator('div[class*="SpecificationBox__main"]')
    box_count = spec_boxes.count()
    
    if box_count == 0:
        spec_boxes = page.locator('section:has(p:text("مشخصات")) div.bg-000')
        box_count = spec_boxes.count()

    for i in range(box_count):
        box = spec_boxes.nth(i)
        
        category_el = box.locator('p[class*="SpecificationBox__title"]')
        if category_el.count() == 0:
            continue
        category_name = category_el.first.inner_text().strip()
        product_data["specifications"][category_name] = {}
        
        rows = box.locator('div[class*="SpecificationAttribute__valuesBox"]')
        for j in range(rows.count()):
            row = rows.nth(j)
            
            key_el = row.locator('p[class*="SpecificationAttribute__value"]')
            val_els = row.locator('div[class*="border-complete"] p, p[class*="SpecificationAttribute__valueText"]')
            
            if key_el.count() > 0 and val_els.count() > 0:
                key_name = key_el.first.inner_text().strip()
                
                values = []
                for k in range(val_els.count()):
                    text = val_els.nth(k).inner_text().strip()
                    if text and text != key_name:
                        values.append(text)
                
                if values:
                    product_data["specifications"][category_name][key_name] = "\n".join(values)

    # ===== NEW: Additional fields =====
    # 1. Persian Product Name
    fa_name_el = page.locator('h1[data-testid="pdp-title"]')
    if fa_name_el.count() > 0:
        raw_fa_name = fa_name_el.first.inner_text().strip()
        # Detect if product is out of stock (ناموجود)
        is_out_of_stock = "ناموجود" in raw_fa_name
        product_data["is_out_of_stock"] = is_out_of_stock
        
        # Clean the name by removing "ناموجود" to avoid displaying it in the UI
        if is_out_of_stock:
            product_data["product_name_fa"] = raw_fa_name.replace("ناموجود", "").strip()
        else:
            product_data["product_name_fa"] = raw_fa_name
    else:
        product_data["product_name_fa"] = ""
        product_data["is_out_of_stock"] = False
    
    # 2. English Product Name
    en_name_el = page.locator('#pdp-variant span.text-neutral-300')
    if en_name_el.count() > 0:
        product_data["product_name_en"] = en_name_el.first.inner_text().strip()

    # 3. Final Current Price
    # NOTE: Digikala changes its frontend markup periodically, so this is
    # the single most likely scraper field to silently break. We try several
    # selectors in order and log exactly what was found/not found, so you can
    # see in your server terminal precisely why a price came back empty.
    price_selectors = [
        '[data-testid="buy-box"] [data-testid="price-final"]',
        '[data-testid="price-final"]',
        '[data-testid="product-price"]',
        '.product-price ins',
        '.c-product-price__value',
    ]
    price_found = False
    for selector in price_selectors:
        price_el = page.locator(selector)
        count = price_el.count()
        if count > 0:
            raw_price_text = price_el.first.inner_text().strip()
            print(f"[scraper]    price selector '{selector}' matched {count} element(s), raw text='{raw_price_text}'")
            if raw_price_text:
                product_data["price"] = raw_price_text
                price_found = True
                break
        else:
            print(f"[scraper]    price selector '{selector}' matched 0 elements")

    if not price_found:
        print(f"[scraper]    ⚠️ NO price selector matched anything for {url}. "
              f"Digikala's markup for this page may have changed -- inspect the live page's "
              f"DOM and update price_selectors in scraper.py.")

    # 4. Main Product Image URL
    img_el = page.locator('picture img[src*="digikala-products"]')
    if img_el.count() > 0:
        img_src = img_el.first.get_attribute("src")
        if img_src:
            product_data["image_url"] = img_src.strip()
            
    if product_data.get("is_out_of_stock"):
        product_data["price"] = ""

    return product_data


# NEW INTERFACE FUNCTION FOR FASTAPI
def run_scraper_pipeline(urls_to_scrape):
    """
    Takes an array of URLs passed from app.py, runs the production 
    playwright engine, and returns the accumulated results dictionary.
    """
    print(f"\n[scraper] ===> run_scraper_pipeline() called with {len(urls_to_scrape)} url(s)")
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        for idx, url in enumerate(urls_to_scrape):
            try:
                data = scrape_digikala_product(page, url)
                results[str(idx + 1)] = data
                spec_count = sum(len(v) for v in data.get("specifications", {}).values())
                print(f"[scraper]  - [{idx+1}] OK: title='{data.get('title','')[:40]}', price='{data.get('price','')}', spec_fields_found={spec_count}")
            except Exception as e:
                print(f"[scraper]  - [{idx+1}] ❌ FAILED for {url}: {e}")
                results[str(idx + 1)] = {"error": str(e), "url": url}
                
        browser.close()
    print(f"[scraper] <=== run_scraper_pipeline() returning {len(results)} result(s)")
    return results


# Allows you to still run "python scraper.py" directly via terminal if you want to test standalone
if __name__ == "__main__":
    if TARGET_URLS:
        final_output = {"_default": run_scraper_pipeline(TARGET_URLS)}
        with open('digikala_scraped_specs.json', 'w', encoding='utf-8') as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
        print("\nStandalone complete!")