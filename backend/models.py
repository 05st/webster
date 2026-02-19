from pydantic import BaseModel
from sqlmodel import Field, SQLModel

class User(SQLModel, table=True):
    id: int = Field(primary_key=True)
    github_id: int = Field(unique=True)
    github_token: str

class WebsiteEntry(SQLModel, table=True):
    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    website_url: str
    repo_name: str

class Message(SQLModel, table=True):
    id: int = Field(primary_key=True)
    website_entry_id: int = Field(foreign_key="websiteentry.id")
    role: str  # "ai" or "human"
    content: str

class Diagnostic(SQLModel, table=True):
    id: int = Field(primary_key=True)
    website_entry_id: int = Field(foreign_key="websiteentry.id")
    short_desc: str
    full_desc: str
    severity: str = Field(default="warning")
    dismissed: bool = Field(default=False)

class MessageResponse(BaseModel):
    role: str
    content: str

class SendMessageRequest(BaseModel):
    content: str

class WebsiteEntryResponse(BaseModel):
    websiteEntryId: int
    websiteUrl: str
    repoName: str
    diagnosticCount: int

class DiagnosticResponse(BaseModel):
    diagnosticId: int
    shortDesc: str
    fullDesc: str
    severity: str

class MeResponse(BaseModel):
    userId: int
    githubId: int
