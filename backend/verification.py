from langchain_core.messages import AIMessage, HumanMessage
from sqlmodel import Session, select
from sqlalchemy import Engine
import requests
import secrets

from agent import run_agent
from constants import BACKEND_URL
from models import Diagnostic, Message, VerificationSettings, WebsiteEntry


SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2}

GH_HEADERS = {"Accept": "application/vnd.github+json"}


def register_github_webhook(repo_name: str, github_token: str) -> tuple[int, str]:
    if not BACKEND_URL:
        raise RuntimeError("BACKEND_URL is not configured")
    webhook_secret = secrets.token_hex(32)
    response = requests.post(
        f"https://api.github.com/repos/{repo_name}/hooks",
        json={
            "name": "web",
            "active": True,
            "events": ["push"],
            "config": {
                "url": f"{BACKEND_URL}/webhook/github",
                "content_type": "json",
                "secret": webhook_secret,
            },
        },
        headers={"Authorization": f"Bearer {github_token}", **GH_HEADERS},
    )
    response.raise_for_status()
    return response.json()["id"], webhook_secret


def deregister_github_webhook(repo_name: str, webhook_id: int, github_token: str) -> None:
    requests.delete(
        f"https://api.github.com/repos/{repo_name}/hooks/{webhook_id}",
        headers={"Authorization": f"Bearer {github_token}", **GH_HEADERS},
    )


async def run_verification(entry_id: int, github_token: str, engine: Engine) -> None:
    with Session(engine) as session:
        entry = session.get(WebsiteEntry, entry_id)
        settings = session.exec(
            select(VerificationSettings).where(VerificationSettings.website_entry_id == entry_id)
        ).first()
        if not entry or not settings:
            return

        website_url = entry.website_url
        repo_name = entry.repo_name
        min_level = SEVERITY_ORDER.get(settings.min_severity, 2)
        auto_fix = settings.auto_fix
        notif_url = settings.webhook_url
        notif_auth_key = settings.webhook_auth_header_key
        notif_auth_value = settings.webhook_auth_header_value
        webhook_format = settings.webhook_format

        existing_ids = {
            d.id for d in session.exec(
                select(Diagnostic).where(Diagnostic.website_entry_id == entry_id, Diagnostic.dismissed == False)
            ).all()
        }
        msgs = session.exec(
            select(Message).where(Message.website_entry_id == entry_id).order_by(Message.id)
        ).all()
        message_history = [
            AIMessage(m.content) if m.role == "ai" else HumanMessage(m.content) for m in msgs
        ]

    trigger_content = "Automated verification: analyze this website for issues."
    with Session(engine) as session:
        session.add(Message(website_entry_id=entry_id, role="human", content=trigger_content, is_automated=True))
        session.commit()
    message_history.append(HumanMessage(trigger_content))

    ai_response = ""
    async for event in run_agent(message_history, website_url, repo_name, engine, entry_id, github_token, False):
        if event["type"] == "done":
            ai_response = event["content"]
    with Session(engine) as session:
        session.add(Message(website_entry_id=entry_id, role="ai", content=ai_response, is_automated=True))
        session.commit()

    with Session(engine) as session:
        all_diags = session.exec(
            select(Diagnostic).where(Diagnostic.website_entry_id == entry_id, Diagnostic.dismissed == False)
        ).all()
        new_diags = [
            (d.short_desc, d.full_desc, d.severity)
            for d in all_diags
            if d.id not in existing_ids and SEVERITY_ORDER.get(d.severity, 0) >= min_level
        ]

    if new_diags and notif_url:
        headers = {"Content-Type": "application/json"}
        if notif_auth_key and notif_auth_value:
            headers[notif_auth_key] = notif_auth_value
        discord_colors = {"error": 0xE74C3C, "warning": 0xFF8C00, "info": 0x3498DB}
        discord_icons = {"error": "🔴", "warning": "🟡", "info": "🔵"}
        for short_desc, full_desc, severity in new_diags:
            try:
                if webhook_format == "discord":
                    payload = {"embeds": [{"title": f"{discord_icons.get(severity, '⚪')} {short_desc}", "description": full_desc, "color": discord_colors.get(severity, 0x7F8C8D), "fields": [{"name": "Severity", "value": severity.upper(), "inline": True}, {"name": "Website", "value": website_url, "inline": True}]}]}
                else:
                    payload = {"event": "diagnostic_alert", "website": website_url, "diagnostic": {"severity": severity, "short_desc": short_desc, "full_desc": full_desc}}
                requests.post(notif_url, json=payload, headers=headers, timeout=10)
            except Exception:
                pass

    if auto_fix and new_diags:
        for short_desc, full_desc, _ in new_diags:
            fix_content = f"Fix this diagnostic: **{short_desc}**\n\n{full_desc}"
            with Session(engine) as session:
                msgs = session.exec(
                    select(Message).where(Message.website_entry_id == entry_id).order_by(Message.id)
                ).all()
                fix_history = [
                    AIMessage(m.content) if m.role == "ai" else HumanMessage(m.content) for m in msgs
                ]
                session.add(Message(website_entry_id=entry_id, role="human", content=fix_content, is_automated=True, is_fix_action=True))
                session.commit()
            fix_history.append(HumanMessage(fix_content))

            fix_response = ""
            async for event in run_agent(fix_history, website_url, repo_name, engine, entry_id, github_token, True):
                if event["type"] == "done":
                    fix_response = event["content"]
            with Session(engine) as session:
                session.add(Message(website_entry_id=entry_id, role="ai", content=fix_response, is_automated=True, is_fix_action=True))
                session.commit()
