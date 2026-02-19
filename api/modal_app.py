import modal
from pathlib import Path

app = modal.App("webster-api")
API_DIR = Path(__file__).parent
image = (
    modal.Image.debian_slim(python_version="3.13")
    .pip_install(
        "fastapi[standard]", "sqlmodel", "requests", "python-dotenv",
        "langchain", "langchain-community", "langchain-openai",
        "langchain-mcp-adapters", "langgraph", "playwright"
    )
    .run_commands("playwright install --with-deps chromium")
    .add_local_dir(str(API_DIR), remote_path="/root/api")
)

db = modal.Volume.from_name("webster-db", create_if_missing=True)
secrets = [modal.Secret.from_name("webster-secrets")]

@app.function(image=image, volumes={"/data": db}, secrets=secrets, min_containers=1)
@modal.concurrent(max_inputs=20)
@modal.asgi_app(label="api")
def fastapi_app():
    import os
    import sys

    if "/root/api" not in sys.path:
        sys.path.insert(0, "/root/api")

    os.environ.setdefault("DATABASE_URL", "sqlite:////data/webster.db")
    from main import api
    return api
