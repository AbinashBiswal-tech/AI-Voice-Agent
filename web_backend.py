import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import chat_storage

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai import types



app = FastAPI(title="AI Voice Agent API")

KEY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    ".gemini_key"
)

api_key = os.environ.get("GEMINI_API_KEY", "").strip()

if not api_key and os.path.exists(KEY_FILE):
    with open(KEY_FILE, "r", encoding="utf-8") as f:
        api_key = f.read().strip()

client = genai.Client(api_key=api_key) if api_key else None

print("WEB GEMINI KEY LOADED:", bool(api_key))


class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None


BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR


app.mount(
    "/static",
    StaticFiles(directory=str(WEB_DIR)),
    name="static"
)

@app.get("/")
def home():
    return FileResponse(WEB_DIR / "index.html")



@app.post("/chat")
def chat(request: ChatRequest):

    if not client:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key is not configured."
        )

    conversation_id = request.conversation_id

    try:
        if not conversation_id:
            conversation_id = chat_storage.create_conversation(
                title=request.message[:50] or "New Chat"
            )

        # Save user message
        chat_storage.save_message(
            conversation_id,
            "user",
            request.message
        )

        # Generate Gemini response
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=request.message
        )

        reply = response.text or "No response received."

        # Save assistant response
        chat_storage.save_message(
            conversation_id,
            "assistant",
            reply
        )

        return {
            "reply": reply,
            "conversation_id": conversation_id
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.get("/conversations")
def conversations():
    try:
        items = chat_storage.get_conversations()

        return [
            {
                "id": item[0],
                "title": item[1],
                "created_at": item[2]
            }
            for item in items
        ]

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.get("/conversations/{conversation_id}")
def conversation_messages(conversation_id: int):
    try:
        messages = chat_storage.get_messages(conversation_id)

        return [
            {
                "role": item[0],
                "content": item[1],
                "created_at": item[2]
            }
            for item in messages
        ]

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


