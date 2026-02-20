import base64
import logging
import time
import requests
from typing import Callable
from playwright.async_api import Page, async_playwright
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_community.tools import BaseTool, tool
from sqlalchemy import Engine
from sqlmodel import Session

from models import *

logger = logging.getLogger(__name__)

async def get_tools(db_engine: Engine, website_entry_id: int, github_token: str, is_fix_action: bool) -> tuple[list[BaseTool], Callable]:
    logger.info("Initializing agent tools for website_entry_id=%s", website_entry_id)

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
    logger.info(
        "Agent tools initialized for website_entry_id=%s with %s github tools",
        website_entry_id,
        len(github_tools),
    )

    def compact_visible_text(text: str, max_chars: int = 8000) -> str:
        lines = [line for line in text.splitlines() if line.strip()]
        return "\n".join(lines)[:max_chars]

    async def ensure_interactive_page() -> Page:
        nonlocal interactive_page
        if interactive_page is None or interactive_page.is_closed():
            logger.info("Creating new interactive page for website_entry_id=%s", website_entry_id)
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
        start = time.time()
        logger.info("Tool open_page start website_entry_id=%s url=%s", website_entry_id, url)
        page = await ensure_interactive_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await settle_page(page)
            title = await page.title()
            logger.info(
                "Tool open_page success website_entry_id=%s url=%s elapsed_ms=%s",
                website_entry_id,
                page.url,
                int((time.time() - start) * 1000),
            )
            return f"Opened page.\nURL: {page.url}\nTitle: {title or 'missing'}"
        except Exception as e:
            logger.exception(
                "Tool open_page failed website_entry_id=%s url=%s elapsed_ms=%s",
                website_entry_id,
                url,
                int((time.time() - start) * 1000),
            )
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
        start = time.time()
        logger.info("Tool click_element start website_entry_id=%s selector=%s", website_entry_id, selector)
        page = await ensure_interactive_page()
        try:
            locator = page.locator(selector).first
            await locator.wait_for(state="visible", timeout=10000)
            await locator.click(timeout=10000)
            await settle_page(page, timeout_ms=6000)
            logger.info(
                "Tool click_element success website_entry_id=%s selector=%s url=%s elapsed_ms=%s",
                website_entry_id,
                selector,
                page.url,
                int((time.time() - start) * 1000),
            )
            return f"Clicked '{selector}'.\nCurrent URL: {page.url}"
        except Exception as e:
            logger.exception(
                "Tool click_element failed website_entry_id=%s selector=%s elapsed_ms=%s",
                website_entry_id,
                selector,
                int((time.time() - start) * 1000),
            )
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
        start = time.time()
        logger.info(
            "Tool type_into start website_entry_id=%s selector=%s text_len=%s clear_first=%s press_enter=%s",
            website_entry_id,
            selector,
            len(text),
            clear_first,
            press_enter,
        )
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
            logger.info(
                "Tool type_into success website_entry_id=%s selector=%s elapsed_ms=%s",
                website_entry_id,
                selector,
                int((time.time() - start) * 1000),
            )
            return f"Typed into '{selector}'."
        except Exception as e:
            logger.exception(
                "Tool type_into failed website_entry_id=%s selector=%s elapsed_ms=%s",
                website_entry_id,
                selector,
                int((time.time() - start) * 1000),
            )
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
        start = time.time()
        logger.info("Tool press_key start website_entry_id=%s key=%s", website_entry_id, key)
        page = await ensure_interactive_page()
        try:
            await page.keyboard.press(key)
            await settle_page(page, timeout_ms=4000)
            logger.info(
                "Tool press_key success website_entry_id=%s key=%s url=%s elapsed_ms=%s",
                website_entry_id,
                key,
                page.url,
                int((time.time() - start) * 1000),
            )
            return f"Pressed key '{key}'.\nCurrent URL: {page.url}"
        except Exception as e:
            logger.exception(
                "Tool press_key failed website_entry_id=%s key=%s elapsed_ms=%s",
                website_entry_id,
                key,
                int((time.time() - start) * 1000),
            )
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
        start = time.time()
        logger.info(
            "Tool wait_for_selector start website_entry_id=%s selector=%s timeout_ms=%s",
            website_entry_id,
            selector,
            timeout_ms,
        )
        page = await ensure_interactive_page()
        try:
            await page.locator(selector).first.wait_for(state="visible", timeout=timeout_ms)
            logger.info(
                "Tool wait_for_selector success website_entry_id=%s selector=%s elapsed_ms=%s",
                website_entry_id,
                selector,
                int((time.time() - start) * 1000),
            )
            return f"Selector became visible: '{selector}'"
        except Exception as e:
            logger.exception(
                "Tool wait_for_selector failed website_entry_id=%s selector=%s elapsed_ms=%s",
                website_entry_id,
                selector,
                int((time.time() - start) * 1000),
            )
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
        start = time.time()
        logger.info(
            "Tool get_current_page_text start website_entry_id=%s max_chars=%s",
            website_entry_id,
            max_chars,
        )
        page = await ensure_interactive_page()
        try:
            text = await page.inner_text("body")
            logger.info(
                "Tool get_current_page_text success website_entry_id=%s text_len=%s elapsed_ms=%s",
                website_entry_id,
                len(text),
                int((time.time() - start) * 1000),
            )
            return compact_visible_text(text, max_chars=max_chars)
        except Exception as e:
            logger.exception(
                "Tool get_current_page_text failed website_entry_id=%s elapsed_ms=%s",
                website_entry_id,
                int((time.time() - start) * 1000),
            )
            return f"Error reading current page text: {e}"

    @tool
    async def get_current_page_url() -> str:
        """
        Return the URL of the currently open interactive page.
        """
        logger.info("Tool get_current_page_url start website_entry_id=%s", website_entry_id)
        page = await ensure_interactive_page()
        logger.info("Tool get_current_page_url success website_entry_id=%s url=%s", website_entry_id, page.url)
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
        start = time.time()
        logger.info("Tool fetch_page start website_entry_id=%s url=%s", website_entry_id, url)
        page = await browser_context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            text = await page.inner_text("body")
            logger.info(
                "Tool fetch_page success website_entry_id=%s url=%s text_len=%s elapsed_ms=%s",
                website_entry_id,
                url,
                len(text),
                int((time.time() - start) * 1000),
            )
            return compact_visible_text(text)
        except Exception as e:
            logger.exception(
                "Tool fetch_page failed website_entry_id=%s url=%s elapsed_ms=%s",
                website_entry_id,
                url,
                int((time.time() - start) * 1000),
            )
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
        start = time.time()
        logger.info("Tool get_page_metadata start website_entry_id=%s url=%s", website_entry_id, url or "<current>")
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

            logger.info(
                "Tool get_page_metadata success website_entry_id=%s url=%s h1_count=%s h2_count=%s elapsed_ms=%s",
                website_entry_id,
                url or page.url,
                len(h1s),
                len(h2s),
                int((time.time() - start) * 1000),
            )
            return "\n".join(parts)
        except Exception as e:
            target = url or "current page"
            logger.exception(
                "Tool get_page_metadata failed website_entry_id=%s url=%s elapsed_ms=%s",
                website_entry_id,
                target,
                int((time.time() - start) * 1000),
            )
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
        start = time.time()
        logger.info(
            "Tool submit_diagnostic start website_entry_id=%s severity=%s short_desc_len=%s full_desc_len=%s",
            website_entry_id,
            severity,
            len(short_desc),
            len(full_desc),
        )
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
            logger.info(
                "Tool submit_diagnostic success website_entry_id=%s diagnostic_id=%s elapsed_ms=%s",
                website_entry_id,
                diagnostic_id,
                int((time.time() - start) * 1000),
            )
            return f"Diagnostic created successfully with id={diagnostic_id}"
        except Exception as e:
            logger.exception(
                "Tool submit_diagnostic failed website_entry_id=%s elapsed_ms=%s",
                website_entry_id,
                int((time.time() - start) * 1000),
            )
            return f"Failed to create diagnostic: {e}"

    async def cleanup():
        logger.info("Cleaning up agent tools for website_entry_id=%s", website_entry_id)
        if interactive_page is not None and not interactive_page.is_closed():
            await interactive_page.close()
        await browser_context.close()
        await browser.close()
        await pw.stop()
        logger.info("Cleanup complete for website_entry_id=%s", website_entry_id)

    @tool
    def gh_create_branch(repo: str, branch: str, base_branch: str = "main") -> str:
        """
        Create a new branch in a GitHub repository.
        Parameters:
            repo: Repository in 'owner/repo' format.
            branch: Name for the new branch.
            base_branch: Branch to branch off from (default: 'main').
        Returns:
            Confirmation message or error.
        """
        logger.info("Tool gh_create_branch start repo=%s branch=%s base=%s", repo, branch, base_branch)
        try:
            headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github+json"}
            ref_resp = requests.get(f"https://api.github.com/repos/{repo}/branches/{base_branch}", headers=headers, timeout=15)
            ref_resp.raise_for_status()
            sha = ref_resp.json()["commit"]["sha"]
            create_resp = requests.post(
                f"https://api.github.com/repos/{repo}/git/refs",
                headers=headers,
                json={"ref": f"refs/heads/{branch}", "sha": sha},
                timeout=15,
            )
            create_resp.raise_for_status()
            logger.info("Tool gh_create_branch success repo=%s branch=%s", repo, branch)
            return f"Branch '{branch}' created from '{base_branch}' in {repo}."
        except Exception as e:
            logger.exception("Tool gh_create_branch failed repo=%s branch=%s", repo, branch)
            return f"Error creating branch '{branch}' in {repo}: {e}"

    @tool
    def gh_create_or_update_file(repo: str, path: str, message: str, content: str, branch: str, sha: str = "") -> str:
        """
        Create or update a file in a GitHub repository.
        Parameters:
            repo: Repository in 'owner/repo' format.
            path: File path within the repository (e.g. 'src/index.html').
            message: Commit message.
            content: New file content (plain text, not base64).
            branch: Branch to commit to.
            sha: Current file SHA (required when updating an existing file; omit when creating a new file).
        Returns:
            Confirmation message with commit SHA, or an error.
        """
        if branch in ("main", "master"):
            return "Error: committing directly to 'main' or 'master' is not allowed. Create a feature branch first."
        logger.info("Tool gh_create_or_update_file start repo=%s path=%s branch=%s", repo, path, branch)
        try:
            headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github+json"}
            body: dict = {
                "message": message,
                "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                "branch": branch,
            }
            if sha:
                body["sha"] = sha
            resp = requests.put(f"https://api.github.com/repos/{repo}/contents/{path}", headers=headers, json=body, timeout=15)
            resp.raise_for_status()
            commit_sha = resp.json()["commit"]["sha"]
            logger.info("Tool gh_create_or_update_file success repo=%s path=%s commit=%s", repo, path, commit_sha)
            return f"File '{path}' committed to branch '{branch}' in {repo}. Commit: {commit_sha}"
        except Exception as e:
            logger.exception("Tool gh_create_or_update_file failed repo=%s path=%s", repo, path)
            return f"Error committing file '{path}' in {repo}: {e}"

    @tool
    def gh_create_pull_request(repo: str, title: str, body: str, head: str, base: str = "main") -> str:
        """
        Open a pull request in a GitHub repository.
        Parameters:
            repo: Repository in 'owner/repo' format.
            title: PR title.
            body: PR description.
            head: Branch with the changes.
            base: Branch to merge into (default: 'main').
        Returns:
            PR URL or an error message.
        """
        logger.info("Tool gh_create_pull_request start repo=%s head=%s base=%s", repo, head, base)
        try:
            headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github+json"}
            resp = requests.post(
                f"https://api.github.com/repos/{repo}/pulls",
                headers=headers,
                json={"title": title, "body": body, "head": head, "base": base},
                timeout=15,
            )
            resp.raise_for_status()
            pr_url = resp.json()["html_url"]
            logger.info("Tool gh_create_pull_request success repo=%s pr_url=%s", repo, pr_url)
            return f"Pull request created: {pr_url}"
        except Exception as e:
            logger.exception("Tool gh_create_pull_request failed repo=%s", repo)
            return f"Error creating pull request in {repo}: {e}"

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
        start = time.time()
        logger.info("Tool get_page_speed start website_entry_id=%s url=%s", website_entry_id, url)
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
            logger.info(
                "Tool get_page_speed success website_entry_id=%s url=%s score=%s elapsed_ms=%s",
                website_entry_id,
                url,
                f"{score:.0f}",
                int((time.time() - start) * 1000),
            )
            return "\n".join(parts)
        except Exception as e:
            logger.exception(
                "Tool get_page_speed failed website_entry_id=%s url=%s elapsed_ms=%s",
                website_entry_id,
                url,
                int((time.time() - start) * 1000),
            )
            return f"Error running PageSpeed audit for {url}: {e}"

    write_tools = [gh_create_branch, gh_create_or_update_file, gh_create_pull_request] if is_fix_action else []

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
    ] + github_tools + write_tools, cleanup
