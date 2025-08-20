from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from urls import api_router, documents_api_router, incidents_api_rooter

app = FastAPI(
    title="Chatbot API",
    description="This is official API for Bank Chatbot services",
    version="1.0.0"
)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(api_router)
app.include_router(documents_api_router)
app.include_router(incidents_api_rooter)