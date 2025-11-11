from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="AI Product Imagery API",
    description="Extract and enhance product images from YouTube videos using AI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api", tags=["Product Imagery"])


@app.on_event("startup")
async def startup_event():
    Path("temp").mkdir(exist_ok=True)

    if not os.getenv("GROQ_API_KEY"):
        print("WARNING: GROQ_API_KEY environment variable not set!")

    if not os.getenv("HUGGINGFACE_API_TOKEN"):
        print("WARNING: HUGGINGFACE_API_TOKEN environment variable not set!")
        print("         Enhancement features will not work without this token.")
        print("         Get your token at: https://huggingface.co/settings/tokens")
    else:
        print("INFO: Using Hugging Face Stable Diffusion XL for image enhancement")

    if os.getenv("GEMINI_API_KEY"):
        print("INFO: GEMINI_API_KEY found, will be used for segmentation operations")
    else:
        print("INFO: GEMINI_API_KEY not set (optional)")


@app.get("/")
async def root():
    return {
        "message": "AI Product Imagery API",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
