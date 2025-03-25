from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import json
import asyncio
from config import setup_logging, create_app, create_ai_model
from models.inventory import CarInventory
from utils.conversation import ConversationManager
from services.chat_service import ChatService

# Initialize components
logger = setup_logging()
app = create_app()
templates = Jinja2Templates(directory="templates")

# Initialize services
model = create_ai_model()
inventory = CarInventory()
conversation_manager = ConversationManager(inventory)
chat_service = ChatService(model, conversation_manager)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        result = await chat_service.process_message(
            data.get("message", ""),
            data.get("conversation_data", {})
        )
        return JSONResponse(result)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request", exc_info=True)
        return JSONResponse(
            {"error": "Invalid JSON format"},
            status_code=400
        )
    except Exception as e:
        logger.error(f"API Error: {e}", exc_info=True)
        return JSONResponse(
            {"error": "Internal server error"},
            status_code=500
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)