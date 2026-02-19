import requests
from typing import Callable
from playwright.async_api import async_playwright
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_community.tools import BaseTool, tool
from sqlalchemy import Engine
from sqlmodel import Session

from models import *

async def get_tools(db_engine: Engine, website_entry_id: int, github_token: str) -> tuple[list[BaseTool], Callable]:
    pw = await async_playwright().start()
    browser = await pw.chromium.launch()

    mcp = MultiServerMCPClient({
        "github": {
            "url": "https://api.githubcopilot.com/mcp/readonly",
            "transport": "streamable_http",
            "headers": {"Authorization": f"Bearer {github_token}"},
        }
    })

    github_tools = await mcp.get_tools()

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
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            text = await page.inner_text("body")
            lines = [l for l in text.splitlines() if l.strip()]
            return "\n".join(lines)[:8000]
        except Exception as e:
            return f"Error fetching {url}: {e}"
        finally:
            await page.close()

    @tool
    async def get_page_metadata(url: str) -> str:
        """
        Fetch a web page and return its SEO metadata: title, meta description,
        Open Graph tags, canonical URL, and heading structure.
        Uses a real browser, so dynamically injected meta tags are included.
        Parameters:
            url: The full URL to inspect
        Returns:
            A summary of the page's metadata, or an error message.
        """
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)

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
            return f"Error fetching metadata for {url}: {e}"
        finally:
            await page.close()

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

    return [fetch_page, get_page_metadata, get_page_speed, submit_diagnostic] + github_tools, cleanup
