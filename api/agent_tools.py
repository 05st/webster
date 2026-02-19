import requests
from typing import Callable
from playwright.async_api import Page, async_playwright
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_community.tools import BaseTool, tool
from sqlalchemy import Engine
from sqlmodel import Session

from models import *

async def get_tools(db_engine: Engine, website_entry_id: int, github_token: str) -> tuple[list[BaseTool], Callable]:
    pw = await async_playwright().start()
    browser = await pw.chromium.launch()
    browser_context = await browser.new_context()
    interactive_page: Page | None = None

    mcp = MultiServerMCPClient({
        "github": {
            "url": "https://api.githubcopilot.com/mcp/readonly",
            "transport": "streamable_http",
            "headers": {"Authorization": f"Bearer {github_token}"},
        }
    })

    github_tools = await mcp.get_tools()

    def compact_visible_text(text: str, max_chars: int = 8000) -> str:
        lines = [line for line in text.splitlines() if line.strip()]
        return "\n".join(lines)[:max_chars]

    async def ensure_interactive_page() -> Page:
        nonlocal interactive_page
        if interactive_page is None or interactive_page.is_closed():
            interactive_page = await browser_context.new_page()
        return interactive_page

    async def settle_page(page: Page, timeout_ms: int = 8000) -> None:
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout_ms)
        except Exception:
            # Some pages never reach full network idle because of background requests.
            pass

    @tool
    async def open_page(url: str) -> str:
        """
        Open a URL in an interactive browser tab and keep that tab alive for follow-up actions.
        Use this before clicking or typing.
        Parameters:
            url: Full URL to open.
        Returns:
            The loaded URL and page title, or an error message.
        """
        page = await ensure_interactive_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await settle_page(page)
            title = await page.title()
            return f"Opened page.\nURL: {page.url}\nTitle: {title or 'missing'}"
        except Exception as e:
            return f"Error opening {url}: {e}"

    @tool
    async def click_element(selector: str) -> str:
        """
        Click an element on the currently open interactive page.
        Use CSS selectors (e.g. 'button[type=submit]', 'a[href=\"/pricing\"]', '[data-testid=\"menu\"]').
        Parameters:
            selector: CSS selector for the element to click.
        Returns:
            Confirmation and the current URL, or an error message.
        """
        page = await ensure_interactive_page()
        try:
            locator = page.locator(selector).first
            await locator.wait_for(state="visible", timeout=10000)
            await locator.click(timeout=10000)
            await settle_page(page, timeout_ms=6000)
            return f"Clicked '{selector}'.\nCurrent URL: {page.url}"
        except Exception as e:
            return f"Error clicking '{selector}': {e}"

    @tool
    async def type_into(selector: str, text: str, clear_first: bool = True, press_enter: bool = False) -> str:
        """
        Type text into an input-like element on the currently open interactive page.
        Parameters:
            selector: CSS selector for the target field.
            text: Text to input.
            clear_first: If true, replace existing content; otherwise append via typing.
            press_enter: If true, press Enter after typing.
        Returns:
            Confirmation message, or an error message.
        """
        page = await ensure_interactive_page()
        try:
            locator = page.locator(selector).first
            await locator.wait_for(state="visible", timeout=10000)
            await locator.click(timeout=10000)
            if clear_first:
                await locator.fill(text, timeout=10000)
            else:
                await locator.type(text, delay=20, timeout=10000)
            if press_enter:
                await locator.press("Enter", timeout=10000)
                await settle_page(page, timeout_ms=6000)
            return f"Typed into '{selector}'."
        except Exception as e:
            return f"Error typing into '{selector}': {e}"

    @tool
    async def press_key(key: str) -> str:
        """
        Press a keyboard key on the currently open interactive page.
        Parameters:
            key: Playwright key name (e.g. 'Enter', 'Tab', 'Escape', 'ArrowDown').
        Returns:
            Confirmation and current URL, or an error message.
        """
        page = await ensure_interactive_page()
        try:
            await page.keyboard.press(key)
            await settle_page(page, timeout_ms=4000)
            return f"Pressed key '{key}'.\nCurrent URL: {page.url}"
        except Exception as e:
            return f"Error pressing key '{key}': {e}"

    @tool
    async def wait_for_selector(selector: str, timeout_ms: int = 10000) -> str:
        """
        Wait for a selector to become visible on the currently open interactive page.
        Parameters:
            selector: CSS selector to wait for.
            timeout_ms: Max wait time in milliseconds.
        Returns:
            Confirmation message, or an error message.
        """
        page = await ensure_interactive_page()
        try:
            await page.locator(selector).first.wait_for(state="visible", timeout=timeout_ms)
            return f"Selector became visible: '{selector}'"
        except Exception as e:
            return f"Error waiting for selector '{selector}': {e}"

    @tool
    async def get_current_page_text(max_chars: int = 8000) -> str:
        """
        Read visible body text from the currently open interactive page.
        Parameters:
            max_chars: Maximum number of characters to return.
        Returns:
            Visible page text, or an error message.
        """
        page = await ensure_interactive_page()
        try:
            text = await page.inner_text("body")
            return compact_visible_text(text, max_chars=max_chars)
        except Exception as e:
            return f"Error reading current page text: {e}"

    @tool
    async def get_current_page_url() -> str:
        """
        Return the URL of the currently open interactive page.
        """
        page = await ensure_interactive_page()
        return page.url or "No URL loaded yet."

    @tool
    async def fetch_page(url: str) -> str:
        """
        Fetch the fully rendered content of a web page and return it as readable text.
        Uses a real browser, so JavaScript-rendered content is included.
        Use this to read the actual content of any page on the website.
        Parameters:
            url: The full URL to fetch (e.g. https://example.com/about)
        Returns:
            The visible text content of the page, or an error message.
        """
        page = await browser_context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            text = await page.inner_text("body")
            return compact_visible_text(text)
        except Exception as e:
            return f"Error fetching {url}: {e}"
        finally:
            await page.close()

    @tool
    async def get_page_metadata(url: str = "") -> str:
        """
        Return SEO metadata (title, meta description, Open Graph tags, canonical URL, headings).
        Uses a real browser, so dynamically injected meta tags are included.
        Parameters:
            url: Optional URL to open first. If omitted, inspect the current interactive page.
        Returns:
            A summary of the page's metadata, or an error message.
        """
        page = await ensure_interactive_page()
        try:
            if url:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await settle_page(page)

            title = await page.title()
            desc = await page.evaluate("document.querySelector('meta[name=\"description\"]')?.content ?? null")
            canonical = await page.evaluate("document.querySelector('link[rel=\"canonical\"]')?.href ?? null")
            og_tags = await page.evaluate("""
                Object.fromEntries(
                    [...document.querySelectorAll('meta[property^="og:"]')]
                        .map(el => [el.getAttribute('property'), el.getAttribute('content')])
                )
            """)
            h1s = await page.evaluate("[...document.querySelectorAll('h1')].map(h => h.innerText.trim())")
            h2s = await page.evaluate("[...document.querySelectorAll('h2')].map(h => h.innerText.trim())")

            parts = [
                f"Title: {title or 'missing'}",
                f"Meta description: {desc or 'missing'}",
                f"Canonical URL: {canonical or 'missing'}",
                f"H1 tags ({len(h1s)}): {h1s[:5]}",
                f"H2 tags ({len(h2s)}): {h2s[:8]}",
            ]
            for prop, content in (og_tags or {}).items():
                parts.append(f"{prop}: {content}")

            return "\n".join(parts)
        except Exception as e:
            target = url or "current page"
            return f"Error fetching metadata for {target}: {e}"

    @tool
    def submit_diagnostic(short_desc: str, full_desc: str, severity: str = "warning") -> str:
        """
        Submit a diagnostic about an issue or suggestion found about the website.
        Parameters:
            short_desc: A short, human-readable description summary of the diagnostic
            full_desc: A full description, which should have all context and information required to address the issue or suggestion
            severity: One of "error" (broken/critical), "warning" (should fix), or "info" (suggestion/minor)
        Returns:
            The return string is the response message from the database regarding the submission.
        """
        try:
            with Session(db_engine) as session:
                diagnostic = Diagnostic(
                    website_entry_id=website_entry_id,
                    short_desc=short_desc,
                    full_desc=full_desc,
                    severity=severity,
                )
                session.add(diagnostic)
                session.commit()
                diagnostic_id = diagnostic.id
            return f"Diagnostic created successfully with id={diagnostic_id}"
        except Exception as e:
            return f"Failed to create diagnostic: {e}"

    async def cleanup():
        if interactive_page is not None and not interactive_page.is_closed():
            await interactive_page.close()
        await browser_context.close()
        await browser.close()
        await pw.stop()

    @tool
    def get_page_speed(url: str) -> str:
        """
        Run a Lighthouse performance audit on a URL using Google PageSpeed Insights.
        Returns a performance score, Core Web Vitals (LCP, FCP, CLS, TBT, TTI, Speed Index),
        and a list of the top improvement opportunities.
        Parameters:
            url: The full URL to audit
        Returns:
            A summary of performance metrics and opportunities, or an error message.
        """
        try:
            response = requests.get(
                "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
                params={"url": url, "strategy": "mobile"},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            audits = data["lighthouseResult"]["audits"]
            score = data["lighthouseResult"]["categories"]["performance"]["score"] * 100
            metrics = {
                "FCP": audits["first-contentful-paint"]["displayValue"],
                "LCP": audits["largest-contentful-paint"]["displayValue"],
                "TBT": audits["total-blocking-time"]["displayValue"],
                "CLS": audits["cumulative-layout-shift"]["displayValue"],
                "SI":  audits["speed-index"]["displayValue"],
                "TTI": audits["interactive"]["displayValue"],
            }
            opportunities = [
                f"- {audits[k]['title']}: {audits[k].get('displayValue', '')}"
                for k in audits
                if audits[k].get("details", {}).get("type") == "opportunity"
                and audits[k].get("score", 1) < 0.9
            ]
            parts = [f"Performance score (mobile): {score:.0f}/100"]
            parts += [f"{k}: {v}" for k, v in metrics.items()]
            if opportunities:
                parts.append("Top opportunities:\n" + "\n".join(opportunities[:5]))
            return "\n".join(parts)
        except Exception as e:
            return f"Error running PageSpeed audit for {url}: {e}"

    return [
        open_page,
        click_element,
        type_into,
        press_key,
        wait_for_selector,
        get_current_page_text,
        get_current_page_url,
        fetch_page,
        get_page_metadata,
        get_page_speed,
        submit_diagnostic,
    ] + github_tools, cleanup
