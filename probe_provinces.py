import asyncio
from playwright.async_api import async_playwright
import json
import sys

async def probe():
    async with async_playwright() as p:
        try:
             # Connect to the already-running Chrome instance
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            
            # Listen for network requests to find the data source
            async def handle_response(response):
                if "json" in response.headers.get("content-type", "") or "api" in response.url:
                    print(f"DEBUG: Response from {response.url}")
                    try:
                        data = await response.json()
                        # check if it contains "Adana" or provinces
                        if isinstance(data, dict):
                            keys = list(data.keys())
                            print(f"Keys: {keys}")
                            if "countries" in keys:
                                print(f"Countries structure: {str(data['countries'])[:500]}")
                            if "provinces" in keys or "locations" in keys:
                                print(f"Found potential provinces data! Keys: {keys}")
                                locs = data.get('locations', [])
                                print(f"DEBUG: Total Count: {data.get('totalCount')}")
                                print("--- Found Items ---")
                                for l in locs:
                                    name = l.get('name', '')
                                    # print(f"Name: {name}")
                                    name = l.get('name', '')
                                    if name and name.startswith("Alhas"):
                                         print(f"DEBUG: FOUND match: {name}", flush=True)
                                         print(f"DETAILS: {repr(l)}", flush=True)
                                         print(f"Desc: {l.get('description')}", flush=True)
                                         print(f"Note: {l.get('note')}", flush=True)
                                         print("DEBUG: END DETAILS", flush=True)
                                print("-------------------")
                    except:
                        pass

            page.on("response", handle_response)
            
            print("Navigating to search page for District containing Alhasuşağı...")
            # Alhasuşağı is in Arguvan, Malatya
            await page.goto("https://www.nisanyanyeradlari.com/?b=Arguvan")
            # Wait for content
            await page.wait_for_timeout(5000)
            
            # Click on the result that says "Kahramanmaraş" and "il" (if possible)
            # Or just click the first link/result
            print("Attempting to click result...")
            
            # Try to find a link or div containing "Kahramanmaraş"
            # We want to see what API call triggers the "drill down"
            
            # Note: The UI might be a list of cards or a table
            content = await page.content()
            # print(content[:1000])

            # Try to find a specific element. Use a broad selector and debug text.
            # Usually result items have a class like 'MuiListItem...' or similar
            
            # Let's just listen for any new API calls after specific wait
            # Assuming the page load 'subdivision_search' IS the drill down?
            # User said "Each province, then each cities".
            
            # Maybe the current page IS the list of districts?
            # If totalCount is 12, maybe those ARE the districts (or some of them).
            # Kahramanmaraş has 11 districts + center. 12 sounds exactly right!
            
            # Let's verify if the 12 items are indeed Districts.
            # I will print the names of the 12 items found in the payload.

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(probe())
