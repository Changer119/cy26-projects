from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.underwriting import router

app = FastAPI(title="健康险智能预核保 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
