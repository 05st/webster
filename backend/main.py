from langchain_core.messages import AIMessage, HumanMessage
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, SQLModel, create_engine, select
from dotenv import load_dotenv
import hashlib
import hmac
import json
import requests

load_dotenv()

from agent import run_agent
from auth import create_session_token, get_current_user_id, get_owned_entry, get_user
from constants import *
from models import *
from verification import SEVERITY_ORDER, deregister_github_webhook, register_github_webhook, run_verification

if not FRONTEND_ORIGIN:
    raise RuntimeError("FRONTEND_URL is required")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is required")
if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
    raise RuntimeError("GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET are required")

engine = create_engine(DATABASE_URL)
SQLModel.metadata.create_all(engine)

api = FastAPI()
api.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Auth ---

@api.get("/integrations/github/oauth2/callback")
def integrations_github_oauth2_callback(code: str) -> RedirectResponse:
    response = requests.post("https://github.com/login/oauth/access_token", data={
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": f"{FRONTEND_ORIGIN}/api/backend/integrations/github/oauth2/callback",
    }, headers={"Accept": "application/json"})
    data = response.json()
    if "access_token" not in data:
        raise HTTPException(status_code=400, detail=f"GitHub token exchange failed: {data}")
    access_token = data["access_token"]

    github_user = requests.get("https://api.github.com/user", headers={
        "Authorization": f"Bearer {access_token}"
    }).json()

    with Session(engine) as session:
        user = session.exec(select(User).where(User.github_id == github_user["id"])).first()
        if user:
            user.github_token = access_token
        else:
            user = User(github_id=github_user["id"], github_token=access_token)
            session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id

    session_token = create_session_token(user_id)
    frontend_is_https = FRONTEND_ORIGIN.startswith("https://")
    redirect = RedirectResponse(f"{FRONTEND_ORIGIN}/")
    redirect.set_cookie(
        SESSION_COOKIE_NAME, session_token,
        httponly=True,
        secure=frontend_is_https,
        samesite="none" if frontend_is_https else "lax",
        max_age=SESSION_TTL_SECONDS,
        path="/",
    )
    return redirect


@api.get("/me")
def get_me(request: Request) -> MeResponse:
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        user = get_user(session, user_id)
    return MeResponse(userId=user.id, githubId=user.github_id)


# --- GitHub ---

@api.get("/github/repos")
def get_github_repos(request: Request) -> list[str]:
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        user = get_user(session, user_id)
    repos = requests.get("https://api.github.com/user/repos?per_page=100", headers={
        "Authorization": f"Bearer {user.github_token}"
    }).json()
    return [repo["full_name"] for repo in repos]


@api.get("/github/app-installed")
def get_github_app_installed(request: Request) -> dict:
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        user = get_user(session, user_id)
    if not GITHUB_APP_SLUG:
        return {"installed": True}
    response = requests.get("https://api.github.com/user/installations", headers={
        "Authorization": f"Bearer {user.github_token}",
        "Accept": "application/vnd.github+json",
    })
    if not response.ok:
        return {"installed": False}
    installations = response.json().get("installations", [])
    installed = any(inst.get("app_slug") == GITHUB_APP_SLUG for inst in installations)
    return {"installed": installed}


# --- Website entries ---

@api.post("/website-entries/add")
def add_website_entry(request: Request, website_url: str, repo_name: str) -> int:
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        entry = WebsiteEntry(user_id=user_id, website_url=website_url, repo_name=repo_name)
        session.add(entry)
        session.commit()
        entry_id = entry.id
    return entry_id


@api.get("/website-entries")
def get_website_entries(request: Request) -> list[WebsiteEntryResponse]:
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        entries = session.exec(select(WebsiteEntry).where(WebsiteEntry.user_id == user_id)).all()
        result = []
        for e in entries:
            count = len(session.exec(
                select(Diagnostic).where(Diagnostic.website_entry_id == e.id, Diagnostic.dismissed == False)
            ).all())
            result.append(WebsiteEntryResponse(
                websiteEntryId=e.id, websiteUrl=e.website_url, repoName=e.repo_name, diagnosticCount=count,
            ))
    return result


# --- Messages ---

@api.get("/messages")
def get_messages(request: Request, website_entry_id: int) -> list[MessageResponse]:
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        get_owned_entry(session, user_id, website_entry_id)
        msgs = session.exec(select(Message).where(Message.website_entry_id == website_entry_id)).all()
    return [MessageResponse(role=m.role, content=m.content, is_automated=m.is_automated, is_fix_action=m.is_fix_action) for m in msgs]


@api.post("/messages/send")
async def send_message(request: Request, website_entry_id: int, is_fix_action: bool, body: SendMessageRequest):
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        entry = get_owned_entry(session, user_id, website_entry_id)
        user = get_user(session, user_id)
        website_url = entry.website_url
        repo_name = entry.repo_name
        github_token = user.github_token

        session.add(Message(website_entry_id=website_entry_id, role="human", content=body.content))
        session.commit()

        msgs = session.exec(
            select(Message).where(Message.website_entry_id == website_entry_id).order_by(Message.id)
        ).all()
        message_history = [(msg.role, msg.content) for msg in msgs]

    messages = [
        AIMessage(content) if role == "ai" else HumanMessage(content)
        for role, content in message_history
    ]

    async def event_generator():
        async for event in run_agent(messages, website_url, repo_name, engine, website_entry_id, github_token, is_fix_action):
            if event["type"] == "done":
                with Session(engine) as session:
                    session.add(Message(website_entry_id=website_entry_id, role="ai", content=event["content"]))
                    session.commit()
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# --- Diagnostics ---

@api.get("/diagnostics")
def get_diagnostics(request: Request, website_entry_id: int) -> list[DiagnosticResponse]:
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        get_owned_entry(session, user_id, website_entry_id)
        diagnostics = session.exec(
            select(Diagnostic).where(Diagnostic.website_entry_id == website_entry_id, Diagnostic.dismissed == False)
        ).all()
    return [DiagnosticResponse(diagnosticId=i.id, shortDesc=i.short_desc, fullDesc=i.full_desc, severity=i.severity) for i in diagnostics]


@api.delete("/diagnostics/{diagnostic_id}")
def dismiss_diagnostic(request: Request, diagnostic_id: int) -> None:
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        diagnostic = session.get(Diagnostic, diagnostic_id)
        if not diagnostic:
            raise HTTPException(status_code=404, detail="Diagnostic not found")
        entry = session.get(WebsiteEntry, diagnostic.website_entry_id)
        if not entry or entry.user_id != user_id:
            raise HTTPException(status_code=404, detail="Diagnostic not found")
        diagnostic.dismissed = True
        session.commit()


# --- Verification settings ---

@api.get("/verification-settings")
def get_verification_settings(request: Request, website_entry_id: int) -> VerificationSettingsResponse:
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        get_owned_entry(session, user_id, website_entry_id)
        settings = session.exec(
            select(VerificationSettings).where(VerificationSettings.website_entry_id == website_entry_id)
        ).first() or VerificationSettings(website_entry_id=website_entry_id)
    return VerificationSettingsResponse(
        enabled=settings.enabled,
        minSeverity=settings.min_severity,
        autoFix=settings.auto_fix,
        pathsInScope=settings.paths_in_scope,
        webhookUrl=settings.webhook_url,
        webhookAuthHeaderKey=settings.webhook_auth_header_key,
        webhookAuthHeaderValue=settings.webhook_auth_header_value,
        triggerKeyword=settings.trigger_keyword,
        webhookFormat=settings.webhook_format,
    )


@api.put("/verification-settings")
def update_verification_settings(request: Request, website_entry_id: int, body: UpdateVerificationSettingsRequest) -> None:
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        entry = get_owned_entry(session, user_id, website_entry_id)
        user = get_user(session, user_id)

        settings = session.exec(
            select(VerificationSettings).where(VerificationSettings.website_entry_id == website_entry_id)
        ).first()
        if not settings:
            settings = VerificationSettings(website_entry_id=website_entry_id)
            session.add(settings)

        was_enabled = settings.enabled
        settings.enabled = body.enabled
        settings.min_severity = body.minSeverity
        settings.auto_fix = body.autoFix
        settings.paths_in_scope = body.pathsInScope
        settings.webhook_url = body.webhookUrl
        settings.webhook_auth_header_key = body.webhookAuthHeaderKey
        settings.webhook_auth_header_value = body.webhookAuthHeaderValue
        settings.trigger_keyword = body.triggerKeyword
        settings.webhook_format = body.webhookFormat

        if not was_enabled and body.enabled:
            try:
                webhook_id, webhook_secret = register_github_webhook(entry.repo_name, user.github_token)
                settings.github_webhook_id = webhook_id
                settings.github_webhook_secret = webhook_secret
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to register GitHub webhook: {e}.")
        elif was_enabled and not body.enabled and settings.github_webhook_id:
            try:
                deregister_github_webhook(entry.repo_name, settings.github_webhook_id, user.github_token)
            except Exception:
                pass
            settings.github_webhook_id = None
            settings.github_webhook_secret = ""

        session.commit()


# --- Webhook ---

@api.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    repo_name = payload.get("repository", {}).get("full_name")
    if not repo_name:
        return {"ok": True}

    commits = payload.get("commits", [])

    with Session(engine) as session:
        entries = session.exec(
            select(WebsiteEntry).where(WebsiteEntry.repo_name == repo_name)
        ).all()

        for entry in entries:
            settings = session.exec(
                select(VerificationSettings).where(
                    VerificationSettings.website_entry_id == entry.id,
                    VerificationSettings.enabled == True,
                )
            ).first()
            if not settings or not settings.github_webhook_secret:
                continue

            sig_header = request.headers.get("X-Hub-Signature-256", "")
            expected = "sha256=" + hmac.new(
                settings.github_webhook_secret.encode(), body, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(sig_header, expected):
                continue

            triggered = any(settings.trigger_keyword in c.get("message", "") for c in commits)
            if triggered:
                user = session.get(User, entry.user_id)
                if user:
                    background_tasks.add_task(run_verification, entry.id, user.github_token, engine)

    return {"ok": True}
