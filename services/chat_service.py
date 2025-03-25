import json
import asyncio
import logging
from typing import Dict, Any

class ChatService:
    def __init__(self, model, conversation_manager):
        self.model = model
        self.conversation_manager = conversation_manager
        self.logger = logging.getLogger(__name__)

    async def process_message(self, message: str, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            state = conversation_data.get("state", "greeting")
            user_info = conversation_data.get("user_info", {})
            vehicles = conversation_data.get("vehicles", [])

            # Process the current state
            response, next_state = self.conversation_manager.process_state(
                state, message, user_info, vehicles
            )

            # Update conversation data
            updated_data = {
                "state": next_state,
                "user_info": user_info,
                "vehicles": vehicles,
                "last_response": state
            }

            # Generate AI response
            ai_response = await self._generate_ai_response(message, updated_data)
            updated_data["content"] = ai_response.strip()

            return updated_data

        except Exception as e:
            self.logger.error(f"Error processing message: {e}", exc_info=True)
            return {
                "content": "I apologize, something went wrong. Please try again.",
                "state": conversation_data.get("state", "greeting")
            }

    async def _generate_ai_response(self, message: str, context: Dict[str, Any]) -> str:
        prompt = f"""
        {SYSTEM_CONTEXT}
        Current Context:
        {json.dumps(context, indent=2)}
        User: {message}
        Assistant:
        """
        return await asyncio.to_thread(self.model.invoke, prompt)
