import asyncio
import random
import re
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from .base_fetcher import BaseFetcher, FetchResult
from config.user_agents import USER_AGENTS
import structlog

logger = structlog.get_logger()


class PlaywrightFetcher(BaseFetcher):
    """Browser-based fetching using Playwright for anti-bot bypassing"""

    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
        timeout: float = 30000,  # 30 seconds in ms
        wait_for: str = "domcontentloaded",
    ):
        self.headless = headless
        self.browser_type = browser_type
        self.timeout = timeout
        self.wait_for = wait_for

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self._init_lock = asyncio.Lock()

    async def _ensure_browser(self):
        """Initialize Playwright browser if not already running"""
        async with self._init_lock:
            if self.playwright is None:
                self.playwright = await async_playwright().start()

                browser_launcher = getattr(self.playwright, self.browser_type)
                self.browser = await browser_launcher.launch(
                    headless=self.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",  # Required for GitHub Actions
                    ],
                )

                # Create persistent context with anti-detection
                self.context = await self.browser.new_context(
                    user_agent=random.choice(USER_AGENTS),
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                    timezone_id="America/New_York",
                    permissions=["geolocation", "notifications"],
                    has_touch=False,
                    is_mobile=False,
                    device_scale_factor=1,
                )

                # Add anti-detection scripts
                await self.context.add_init_script("""
                    // Remove webdriver property
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });

                    // Mock plugins
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });

                    // Mock languages
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });

                    // Chrome runtime
                    window.chrome = {
                        runtime: {}
                    };
                """)

                logger.info("playwright_browser_started", browser_type=self.browser_type)

    async def fetch(self, url: str, **kwargs) -> FetchResult:
        """Fetch using Playwright browser automation"""
        await self._ensure_browser()

        page: Optional[Page] = None
        try:
            page = await self.context.new_page()

            # Add extra stealth headers
            await page.set_extra_http_headers(
                {
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept": "application/rss+xml,application/atom+xml,application/xml,text/xml,text/html;q=0.9,*/*;q=0.8",
                }
            )

            logger.info("playwright_fetch_started", url=url)

            # Navigate to page
            response = await page.goto(
                url, wait_until=self.wait_for, timeout=self.timeout
            )

            # Prefer raw response body if it is already valid RSS/Atom XML
            raw_body = ""
            if response is not None:
                try:
                    raw_body = await response.text()
                except Exception:
                    raw_body = ""

            if self._looks_like_feed_xml(raw_body):
                logger.info(
                    "playwright_fetch_success",
                    url=url,
                    content_length=len(raw_body),
                )
                return FetchResult(
                    success=True,
                    content=raw_body,
                    status_code=response.status if response else 200,
                    method_used="playwright",
                    metadata={"url": page.url},
                )

            # Handle cookie consent popups
            await self._handle_cookie_consent(page)

            # Optional: Add human-like delay
            if kwargs.get("human_delay", False):
                await asyncio.sleep(random.uniform(1, 3))

            # Get page content
            content = await page.content()

            # Extract XML from HTML wrapper if present (e.g., RSS feeds rendered in browser)
            content = self._extract_xml_from_html(content)

            # Check if we got blocked
            if self._is_blocked(content, response.status if response else 200):
                logger.warning("playwright_blocked_detected", url=url)
                return FetchResult(
                    success=False,
                    status_code=403,
                    error="Bot detection triggered",
                    method_used="playwright",
                )

            logger.info("playwright_fetch_success", url=url, content_length=len(content))

            return FetchResult(
                success=True,
                content=content,
                status_code=response.status if response else 200,
                method_used="playwright",
                metadata={
                    "url": page.url,
                    "title": await page.title(),
                },
            )

        except asyncio.TimeoutError:
            logger.error("playwright_timeout", url=url)
            return FetchResult(
                success=False, error="Page load timeout", method_used="playwright"
            )

        except Exception as e:
            logger.error(
                "playwright_error",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
            )
            return FetchResult(
                success=False, error=str(e), method_used="playwright"
            )

        finally:
            if page:
                await page.close()

    async def _handle_cookie_consent(self, page: Page):
        """Attempt to dismiss common cookie consent banners"""
        cookie_selectors = [
            'button:has-text("Accept")',
            'button:has-text("Accept All")',
            'button:has-text("I Agree")',
            'button:has-text("OK")',
            "#onetrust-accept-btn-handler",
            ".cookie-accept",
            '[id*="cookie"][id*="accept"]',
        ]

        for selector in cookie_selectors:
            try:
                await page.click(selector, timeout=1000)
                logger.info("cookie_consent_dismissed", selector=selector)
                break
            except Exception:
                continue

    def _looks_like_feed_xml(self, content: str) -> bool:
        """Return True if content contains RSS or Atom XML feed markers."""
        if not content:
            return False
        sample = content[:4000].lower()
        return any(
            tag in sample
            for tag in ("<rss", "<feed", "<rdf:rdf", "<channel>", "<item>", "<entry>")
        )

    def _is_blocked(self, content: str, status_code: int = 200) -> bool:
        """Detect if we've been blocked by anti-bot measures without false-positiving on RSS feeds."""
        if self._looks_like_feed_xml(content):
            return False

        if status_code in (401, 403, 429, 503):
            return True

        # Inspect only <title> and short challenge bodies to avoid matching normal article words
        title_match = re.search(
            r"<title[^>]*>(.*?)</title>", content[:5000], re.IGNORECASE | re.DOTALL
        )
        title_text = title_match.group(1).lower() if title_match else ""
        title_block_markers = [
            "access denied",
            "attention required",
            "just a moment",
            "security check",
            "bot verification",
            "ddos-guard",
        ]
        if any(m in title_text for m in title_block_markers):
            return True

        # For short non-XML responses, check strict challenge phrases
        if len(content) < 15000:
            content_lower = content.lower()
            strict_markers = [
                "please verify you are a human",
                "cf-browser-verification",
                "enable javascript and cookies to continue",
                "ray id:",
            ]
            if any(m in content_lower for m in strict_markers):
                return True

        return False

    def _extract_xml_from_html(self, content: str) -> str:
        """
        Extract XML content from Chromium HTML wrapper if present.
        Handles both <pre> tags and Chromium's #webkit-xml-viewer-source-xml container.
        """
        content_lower = content.lower()
        if "webkit-xml-viewer-source-xml" in content_lower or (
            "<pre" in content_lower and ("<?xml" in content or "&lt;?xml" in content or "&lt;rss" in content)
        ):
            from bs4 import BeautifulSoup

            try:
                soup = BeautifulSoup(content, "html.parser")
                xml_div = soup.find(id="webkit-xml-viewer-source-xml")
                if xml_div:
                    inner_xml = xml_div.decode_contents()
                    if self._looks_like_feed_xml(inner_xml):
                        logger.info("extracted_xml_from_webkit_viewer")
                        return inner_xml

                pre_tag = soup.find("pre")
                if pre_tag:
                    xml_content = pre_tag.get_text()
                    if xml_content.strip().startswith("<?xml") or self._looks_like_feed_xml(xml_content):
                        logger.info("extracted_xml_from_html_wrapper")
                        return xml_content
            except Exception:
                pass

        return content

    async def close(self):
        """Close Playwright browser and cleanup"""
        if self.context:
            await self.context.close()
            self.context = None

        if self.browser:
            await self.browser.close()
            self.browser = None

        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

        logger.info("playwright_browser_closed")

    @property
    def name(self) -> str:
        return "playwright"
