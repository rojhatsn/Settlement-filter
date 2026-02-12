import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            val = stealth(page)
            if asyncio.iscoroutine(val):
                await val
            print("Stealth applied successfully")
        except Exception as e:
            print(f"Error: {e}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
