from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

load_dotenv()

from app.db import create_tables
from app.routes import auth, projects, references, questionnaires, answers, export


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        create_tables()
        print("✅ Database tables ready")
    except Exception as e:
        print(f"⚠️  Database startup warning: {e}")
        print("   App will start — DB operations will fail until connection is fixed")
    yield


app = FastAPI(
    title="QuestionnaireAI",
    description="Structured Questionnaire Answering Tool powered by Groq LLM",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:5173"),
        "https://*.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(references.router, prefix="/api/projects", tags=["Reference Documents"])
app.include_router(questionnaires.router, prefix="/api/projects", tags=["Questionnaires"])
app.include_router(answers.router, prefix="/api/projects", tags=["Answers"])
app.include_router(export.router, prefix="/api/projects", tags=["Export"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "QuestionnaireAI API is running"}
