from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
from langchain_ollama import OllamaLLM

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger("car_dealership_chatbot")

def create_app():
    app = FastAPI(title="Car Dealership AI Chatbot")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    return app

def create_ai_model():
    return OllamaLLM(
        model="llama3",
        temperature=0.7,
        max_tokens=1024
    )

SYSTEM_CONTEXT = '''You are an AI assistant for a car dealership. Your role is to help customers find their ideal vehicle based on their preferences and requirements.

Guidelines:
1. Respond conversationally and professionally.
2. Gather key details efficiently:
   - Buy or lease preference
   - Vehicle type (sedan, SUV, truck, etc.)
   - Budget or payment preference
   - Specific features or requirements
3. Ask questions one by one to avoid overwhelming the user.
4. Provide up to three recommendations initially.
5. Adjust recommendations dynamically based on user feedback.
6. End conversations gracefully when the user indicates they're finished.

Maintain the following conversation structure:
1. Gather missing information if necessary.
2. If the user provides all necessary information, provide recommendations.
3. If the user asks for more details, provide detailed information about the selected vehicle.
4. If the user asks about deals or financing, provide relevant information.
5. If user doesn't want any specific features, leave it as none.

When providing recommendations:
- Highlight key features, price, and financing/lease options.
- Present vehicles sorted by relevance to the user's preferences.
- Offer additional details or alternatives if asked.'''
