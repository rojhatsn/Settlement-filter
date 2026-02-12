import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import json
import urllib.parse
from provinces import PROVINCES
import os

# Configuration
BASE_URL = "https://www.nisanyanyeradlari.com/?b="
OUTPUT_FILE = "Turkey_Settlements_Detailed.csv"

def extract_list_items(data_dict):
    """Helper to extract items from before/after structures."""
    if not data_dict:
        return ""
    
    results = []
    
    # Process both 'before' and 'after' keys
    for key in ['before', 'after']:
        section = data_dict.get(key)
        if not section:
            continue
            
        if isinstance(section, list):
             results.extend([str(i) for i in section])
        elif isinstance(section, dict):
            items = section.get('items', [])
            # print(f"DEBUG: Extracting from {key}, items: {len(items)}") # Uncomment for verbose debugging
            for i in items:
                if isinstance(i, dict):
                    # The item itself is the name object (e.g. {'tr': 'Yörük'})
                    extracted = i.get('tr')
                    if extracted:
                        results.append(extracted)
                    else:
                         results.append(str(i))
                elif isinstance(i, str):
                    results.append(i)
                else:
                    results.append(str(i))
    
    return ", ".join(results)

def extract_old_names(old_names_list):
    """Parses the detailed oldNames list into a readable string."""
    if not old_names_list:
        return "N/A"
    
    results = []
    for item in old_names_list:
        name = item.get('name', '')
        # Add language if present
        langs = [lang.get('tr', '') for lang in item.get('languages', []) if lang.get('tr')]
        lang_str = f" ({', '.join(langs)})" if langs else ""
        
        # Add definition/note if present
        defn = item.get('definition', {}).get('tr', '')
        defn_str = f" [{defn}]" if defn else ""
        
        # Add romanized text if different
        rom = item.get('romanizedText', '')
        rom_str = f" / {rom}" if rom and rom != name else ""
        
        full_entry = f"{name}{lang_str}{rom_str}{defn_str}"
        results.append(full_entry)
        
    return " | ".join(results)

async def run_scraper():
    print(f"🚀 Starting Hierarchical Scraper for {len(PROVINCES)} provinces...")
    # ... (rest of the file)
    
    # Load existing data to resume if crash happens
    if os.path.exists(OUTPUT_FILE):
        existing_df = pd.read_csv(OUTPUT_FILE, encoding='utf-16')
        processed_provinces = existing_df['Province'].unique().tolist()
        print(f"ℹ️ Found existing data. Skipping {len(processed_provinces)} provinces: {processed_provinces}")
    else:
        existing_df = pd.DataFrame()
        processed_provinces = []

    async with async_playwright() as p:
        print("DEBUG: Connecting to existing Chrome instance...")
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            print("DEBUG: Connected to Chrome!")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
        except Exception as e:
            print(f"❌ Could not connect to Chrome: {e}")
            print("Make sure you launched Chrome with: --remote-debugging-port=9222")
            return

        # Wait for any previous requests to settle
        await page.wait_for_timeout(2000)

        for province in PROVINCES:
            if province in processed_provinces:
                continue
            
            print(f"\n📍 Processing Province: {province}")
            province_data = []
            
            try:
                # 1. Get Districts for the Province
                target_url = BASE_URL + urllib.parse.quote(province)
                
                # Setup predicate for Province API call
                encoded_province = urllib.parse.quote(province)
                
                def province_predicate(response):
                    # Filter for only XHR/Fetch/JSON
                    if "subdivision_search" not in response.url:
                        return False
                    if response.status != 200:
                        return False
                    
                    # Debug log (will be spammy but useful)
                    # print(f"DEBUG: Checking URL: {response.url}")
                    
                    match = encoded_province in response.url
                    if match:
                        print(f"   ✅ Matched URL: {response.url}")
                    return match

                async with page.expect_response(province_predicate, timeout=15000) as response_info:
                    print(f"   Navigating to {province}...")
                    await page.goto(target_url)
                
                response = await response_info.value
                # Verify just in case
                if encoded_province not in response.url:
                     print(f"      ⚠️ Warning: Captured response URL {response.url} looks mismatched for {province}")
                
                data = await response.json()
                
                # Extract Districts
                locations = data.get('locations', [])
                districts = [loc for loc in locations if loc.get('locationType', {}).get('name', {}).get('tr') == 'ilçe']
            
                print(f"   Found {len(districts)} districts in {province}.")
                
                # 2. Iterate Districts
                for district_node in districts:
                    district_name = district_node.get('name')
                    print(f"   👉 Drilling down into District: {district_name}")
                    
                    district_url = BASE_URL + urllib.parse.quote(district_name)
                    encoded_district = urllib.parse.quote(district_name)

                    def district_predicate(response):
                        if "subdivision_search" not in response.url:
                            return False
                        if response.status != 200:
                            return False
                        
                        match = encoded_district in response.url
                        if match:
                             print(f"   ✅ Matched District URL: {response.url}")
                        return match
                    
                    try:
                         async with page.expect_response(district_predicate, timeout=15000) as d_response_info:
                            await page.goto(district_url)
                            # Wait a bit to be human-like
                            await page.wait_for_timeout(1500)

                         d_response = await d_response_info.value
                         d_data = await d_response.json()
                         d_locations = d_data.get('locations', [])
                         
                         # Filter for settlements (villages, neighborhoods, etc.)
                         # Exclude the district itself if it appears
                         villages = [l for l in d_locations if l.get('name') != district_name]
                         
                         print(f"      Captured {len(villages)} settlements.")
                         
                         for v in villages:
                             # Extract detailed info
                             record = {
                                 "Province": province,
                                 "District": district_name,
                                 "Name": v.get('name'),
                                 "Type": v.get('locationType', {}).get('name', {}).get('tr', 'N/A'),
                                 "Old_Name": extract_old_names(v.get('oldNames')),
                                 "Description": v.get('note', {}).get('tr', 'N/A'),
                                 "Tribes": extract_list_items(v.get('tribes')),
                                 "Ethnicity": extract_list_items(v.get('communities')),
                                 "Coordinates": str(v.get('coordinates', [])),
                                 "Original_Text": v.get('originalText', 'N/A')
                             }
                             province_data.append(record)

                    except Exception as e:
                        print(f"      ⚠️ Error scraping district {district_name}: {e}")
                        continue

            except Exception as e:
                print(f"   ❌ Error scraping province {province}: {e}")
            
            # Save Province Data immediately to avoid data loss
            if province_data:
                new_df = pd.DataFrame(province_data)
                
                # Append to CSV
                # If file doesn't exist, write header. If it does, skip header.
                header = not os.path.exists(OUTPUT_FILE)
                new_df.to_csv(OUTPUT_FILE, mode='a', header=header, index=False, encoding='utf-16')
                print(f"   💾 Saved {len(new_df)} records for {province}.")
            
            # Add a delay between provinces
            await page.wait_for_timeout(2000)

        print("\n✅ All finished!")

if __name__ == "__main__":
    asyncio.run(run_scraper())
