# src/utils/anti_bot.py
# ====================
# Purpose: Bypass anti-bot protections (Cloudflare, Datadome, etc.)
# Why: Many sites block automated scrapers
# Strategy: Browser emulation, human-like behavior, rotating proxies

import asyncio
import random
from typing import Optional
from loguru import logger
from playwright.async_api import async_playwright, Browser, Page

class AntiBot:
    """
    Anti-bot protection bypass utility
    
    Features:
    - Browser emulation with Playwright
    - Human-like behavior (scrolling, mouse movements)
    - User-Agent rotation
    - Proxy support
    - Stealth mode
    """
    
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        self.browser: Optional[Browser] = None
        self.is_headless = False
    
    async def scrape_with_playwright(
        self,
        url: str,
        headless: bool = True,
        wait_until: str = 'networkidle',
        timeout: int = 30000
    ) -> Optional[str]:
        """
        Scrape a URL using Playwright with stealth mode
        
        Args:
            url: URL to scrape
            headless: Run in headless mode
            wait_until: When to consider navigation complete
            timeout: Navigation timeout in ms
        
        Returns:
            HTML content or None
        """
        try:
            async with async_playwright() as p:
                # Launch browser with stealth args
                browser = await p.chromium.launch(
                    headless=headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-site-isolation-trials'
                    ]
                )
                
                # Create context with realistic viewport
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=self.get_random_user_agent(),
                    locale='en-US',
                    timezone_id='America/New_York',
                    java_script_enabled=True,
                    extra_http_headers={
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    }
                )
                
                # Create page
                page = await context.new_page()
                
                # Add stealth scripts
                await self._add_stealth_scripts(page)
                
                # Navigate to URL
                logger.debug(f"Navigating to {url} with Playwright")
                response = await page.goto(url, wait_until=wait_until, timeout=timeout)
                
                if not response or response.status >= 400:
                    logger.warning(f"Playwright navigation failed: {response.status if response else 'No response'}")
                    await browser.close()
                    return None
                
                # Human-like behavior
                await self._human_like_behavior(page)
                
                # Get content
                content = await page.content()
                await browser.close()
                
                return content
                
        except Exception as e:
            logger.error(f"Playwright error for {url}: {e}")
            return None
    
    async def _add_stealth_scripts(self, page: Page):
        """
        Add scripts to hide automation detection
        
        Args:
            page: Playwright page object
        """
        # Override navigator.webdriver
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # Override chrome detection
        await page.add_init_script("""
            window.chrome = {
                runtime: {}
            };
        """)
        
        # Override permissions
        await page.add_init_script("""
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
    
    async def _human_like_behavior(self, page: Page):
        """
        Simulate human-like behavior on the page
        
        Args:
            page: Playwright page object
        """
        # Random scroll
        await self._scroll_page(page)
        
        # Random mouse movements
        await self._move_mouse_randomly(page)
        
        # Random wait
        await asyncio.sleep(random.uniform(1, 3))
    
    async def _scroll_page(self, page: Page):
        """
        Scroll page like a human
        
        Args:
            page: Playwright page object
        """
        # Get page height
        height = await page.evaluate('document.body.scrollHeight')
        
        # Scroll in small increments
        for _ in range(random.randint(2, 4)):
            # Random scroll amount
            scroll_amount = random.randint(200, 500)
            current_scroll = await page.evaluate('window.scrollY')
            
            if current_scroll + scroll_amount < height:
                await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
            else:
                await page.evaluate(f'window.scrollTo(0, {height * 0.8})')
                break
            
            # Random pause between scrolls
            await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # Sometimes scroll back up a bit
        if random.random() < 0.3:
            await page.evaluate('window.scrollBy(0, -100)')
            await asyncio.sleep(0.5)
    
    async def _move_mouse_randomly(self, page: Page):
        """
        Move mouse like a human
        
        Args:
            page: Playwright page object
        """
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 1800)
            y = random.randint(100, 900)
            await page.mouse.move(x, y, steps=random.randint(10, 20))
            await asyncio.sleep(random.uniform(0.1, 0.5))
    
    def get_random_user_agent(self) -> str:
        """
        Get random user agent
        
        Returns:
            Random user agent string
        """
        return random.choice(self.user_agents)

# Example usage:
# from src.utils.anti_bot import AntiBot
# import asyncio
# 
# async def main():
#     anti_bot = AntiBot()
#     html = await anti_bot.scrape_with_playwright(
#         "https://www.ycombinator.com/companies",
#         headless=True
#     )
#     print(f"Fetched {len(html)} characters" if html else "Failed")
# 
# asyncio.run(main())