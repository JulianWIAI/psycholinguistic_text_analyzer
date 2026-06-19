"""
PsychoLinguistic Analysis Engine — Entry Point
Boots the FastAPI application and serves the UI.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

from api.routes import router
from api.compare_routes import router as compare_router

app = FastAPI(
    title="PsychoLinguistic Analysis Engine",
    description=(
        "Advanced text analysis engine for detecting hidden psychological states, "
        "steganographic dissonance, and morpho-psychological patterns."
    ),
    version="1.0.0",
)

app.include_router(router, prefix="/api")
app.include_router(compare_router, prefix="/api")

templates = Jinja2Templates(directory="templates")


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
