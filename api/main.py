from langchain_core.messages import AIMessage, HumanMessage
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, SQLModel, create_engine, select
from dotenv import load_dotenv
import requests
import os

from agent import run_agent
from models import *

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///webster.db")

engine = create_engine(DATABASE_URL)
SQLModel.metadata.create_all(engine)

api = FastAPI()

api.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@api.get("/integrations/github/oauth2/callback")
def integrations_github_oauth2_callback(code: str) -> RedirectResponse:
    response = requests.post("https://github.com/login/oauth/access_token", data={
        "client_id": os.getenv("GITHUB_CLIENT_ID"),
        "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
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

    redirect = RedirectResponse(FRONTEND_URL)
    redirect.set_cookie("user_id", str(user_id))
    return redirect

@api.get("/github/repos")
def get_github_repos(user_id: int) -> list[str]:
    with Session(engine) as session:
        user = session.get(User, user_id)
    repos = requests.get("https://api.github.com/user/repos?per_page=100", headers={
        "Authorization": f"Bearer {user.github_token}"
    }).json()
    return [repo["full_name"] for repo in repos]

@api.post("/website-entries/add")
def add_website_entry(user_id: int, website_url: str, repo_name: str) -> int:
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
def get_website_entries(user_id: int) -> list[WebsiteEntryResponse]:
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
def get_messages(website_entry_id: int) -> list[MessageResponse]:
    with Session(engine) as session:
        msgs = session.exec(select(Message).where(Message.website_entry_id == website_entry_id)).all()
    return [MessageResponse(role=m.role, content=m.content) for m in msgs]

@api.post("/messages/send")
async def send_message(website_entry_id: int, body: SendMessageRequest) -> MessageResponse:
    with Session(engine) as session:
        human_msg = Message(website_entry_id=website_entry_id, role="human", content=body.content)
        session.add(human_msg)
        session.commit()

        entry = session.get(WebsiteEntry, website_entry_id)
        user = session.get(User, entry.user_id)
        msgs = session.exec(select(Message).where(Message.website_entry_id == website_entry_id)).all()

    messages = [
        AIMessage(msg.content) if msg.role == "ai" else HumanMessage(msg.content)
        for msg in msgs
    ]
    reply_content = await run_agent(messages, entry.website_url, entry.repo_name, engine, website_entry_id, user.github_token)

    with Session(engine) as session:
        ai_msg = Message(website_entry_id=website_entry_id, role="ai", content=reply_content)
        session.add(ai_msg)
        session.commit()

    return MessageResponse(role="ai", content=reply_content)

@api.get("/diagnostics")
def get_diagnostics(website_entry_id: int) -> list[DiagnosticResponse]:
    with Session(engine) as session:
        diagnostics = session.exec(
            select(Diagnostic).where(Diagnostic.website_entry_id == website_entry_id, Diagnostic.dismissed == False)
        ).all()
    return [DiagnosticResponse(diagnosticId=i.id, shortDesc=i.short_desc, fullDesc=i.full_desc, severity=i.severity) for i in diagnostics]

@api.delete("/diagnostics/{diagnostic_id}")
def dismiss_diagnostic(diagnostic_id: int) -> None:
    with Session(engine) as session:
        diagnostic = session.get(Diagnostic, diagnostic_id)
        if diagnostic:
            diagnostic.dismissed = True
            session.commit()
