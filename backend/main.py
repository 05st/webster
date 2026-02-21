from langchain_core.messages import AIMessage, HumanMessage
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, SQLModel, create_engine, select
from dotenv import load_dotenv
import json
import requests
import jwt
import time
from jwt import ExpiredSignatureError, InvalidTokenError

load_dotenv()

from agent import run_agent
from models import *
from constants import *

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

def create_session_token(user_id: int) -> str:
    expires_at = int(time.time()) + SESSION_TTL_SECONDS
    payload = {
        "sub": str(user_id),
        "exp": expires_at,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_current_user_id(request: Request) -> int:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session token")

    user_id = decoded.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid session token")
    try:
        return int(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session token")

def get_owned_entry(session: Session, user_id: int, website_entry_id: int) -> WebsiteEntry:
    entry = session.get(WebsiteEntry, website_entry_id)
    if not entry or entry.user_id != user_id:
        raise HTTPException(status_code=404, detail="Website entry not found")
    return entry

@api.get("/integrations/github/oauth2/callback")
def integrations_github_oauth2_callback(code: str) -> RedirectResponse:
    response = requests.post("https://github.com/login/oauth/access_token", data={
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code
    }, headers={"Accept": "application/json"})

    access_token = response.json()["access_token"]

    github_user = requests.get("https://api.github.com/user", headers={
        "Authorization": f"Bearer {access_token}"
    }).json()
    github_id = github_user["id"]

    with Session(engine) as session:
        user = session.exec(select(User).where(User.github_id == github_id)).first()
        if user:
            user.github_token = access_token
        else:
            user = User(github_id=github_id, github_token=access_token)
            session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id

    session_token = create_session_token(user_id)
    redirect_url = f"{FRONTEND_ORIGIN}/"
    redirect = RedirectResponse(redirect_url)
    frontend_is_https = FRONTEND_ORIGIN.startswith("https://")
    redirect.set_cookie(
        SESSION_COOKIE_NAME,
        session_token,
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
        user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return MeResponse(userId=user.id, githubId=user.github_id)

@api.get("/github/repos")
def get_github_repos(request: Request) -> list[str]:
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    repos = requests.get("https://api.github.com/user/repos?per_page=100", headers={
        "Authorization": f"Bearer {user.github_token}"
    }).json()
    return [repo["full_name"] for repo in repos]

@api.post("/website-entries/add")
def add_website_entry(request: Request, website_url: str, repo_name: str) -> int:
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        entry = WebsiteEntry(
            user_id=user_id,
            website_url=website_url,
            repo_name=repo_name
        )
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
                websiteEntryId=e.id,
                websiteUrl=e.website_url,
                repoName=e.repo_name,
                diagnosticCount=count,
            ))
    return result

@api.get("/messages")
def get_messages(request: Request, website_entry_id: int) -> list[MessageResponse]:
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        get_owned_entry(session, user_id, website_entry_id)
        msgs = session.exec(select(Message).where(Message.website_entry_id == website_entry_id)).all()
    return [MessageResponse(role=m.role, content=m.content) for m in msgs]

@api.post("/messages/send")
async def send_message(request: Request, website_entry_id: int, is_fix_action: bool, body: SendMessageRequest):
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        entry = get_owned_entry(session, user_id, website_entry_id)
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        website_url = entry.website_url
        repo_name = entry.repo_name
        github_token = user.github_token

        human_msg = Message(website_entry_id=website_entry_id, role="human", content=body.content)
        session.add(human_msg)
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
                    ai_msg = Message(website_entry_id=website_entry_id, role="ai", content=event["content"])
                    session.add(ai_msg)
                    session.commit()
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@api.get("/diagnostics")
def get_diagnostics(request: Request, website_entry_id: int) -> list[DiagnosticResponse]:
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        get_owned_entry(session, user_id, website_entry_id)
        diagnostics = session.exec(
            select(Diagnostic).where(Diagnostic.website_entry_id == website_entry_id, Diagnostic.dismissed == False)
        ).all()
    return [DiagnosticResponse(diagnosticId=i.id, shortDesc=i.short_desc, fullDesc=i.full_desc, severity=i.severity) for i in diagnostics]

@api.get("/verification-settings")
def get_verification_settings(request: Request, website_entry_id: int) -> VerificationSettingsResponse:
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        get_owned_entry(session, user_id, website_entry_id)
        settings = session.exec(
            select(VerificationSettings).where(VerificationSettings.website_entry_id == website_entry_id)
        ).first()
        if not settings:
            settings = VerificationSettings(website_entry_id=website_entry_id)
    return VerificationSettingsResponse(
        enabled=settings.enabled,
        minSeverity=settings.min_severity,
        autoFix=settings.auto_fix,
        pathsInScope=settings.paths_in_scope,
        webhookUrl=settings.webhook_url,
        webhookAuthHeaderKey=settings.webhook_auth_header_key,
        webhookAuthHeaderValue=settings.webhook_auth_header_value,
    )

@api.put("/verification-settings")
def update_verification_settings(request: Request, website_entry_id: int, body: UpdateVerificationSettingsRequest) -> None:
    user_id = get_current_user_id(request)
    with Session(engine) as session:
        get_owned_entry(session, user_id, website_entry_id)
        settings = session.exec(
            select(VerificationSettings).where(VerificationSettings.website_entry_id == website_entry_id)
        ).first()
        if not settings:
            settings = VerificationSettings(website_entry_id=website_entry_id)
            session.add(settings)
        settings.enabled = body.enabled
        settings.min_severity = body.minSeverity
        settings.auto_fix = body.autoFix
        settings.paths_in_scope = body.pathsInScope
        settings.webhook_url = body.webhookUrl
        settings.webhook_auth_header_key = body.webhookAuthHeaderKey
        settings.webhook_auth_header_value = body.webhookAuthHeaderValue
        session.commit()

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
