import re
from difflib import get_close_matches
from typing import Optional, Dict, List, Any

class ConversationManager:
    def __init__(self, inventory):
        self.inventory = inventory

    @staticmethod
    def determine_budget_category(budget_str: str) -> str:
        try:
            budget = float(re.sub(r"[^\d.]", "", budget_str))
            return "economy" if budget <= 35000 else "luxury"
        except ValueError:
            raise ValueError("Invalid budget format")

    @staticmethod
    def find_closest_vehicle(message: str, vehicles: List[Dict[str, Any]]) -> Optional[str]:
        if not vehicles:
            return None
            
        vehicle_names = [vehicle["name"] for vehicle in vehicles]
        closest_matches = get_close_matches(
            message.lower(),
            [name.lower() for name in vehicle_names],
            n=1,
            cutoff=0.5
        )
        
        if closest_matches:
            match_index = [name.lower() for name in vehicle_names].index(closest_matches[0])
            return vehicle_names[match_index]
        return None

    def process_state(self, state: str, message: str, user_info: dict, vehicles: list) -> tuple:
        if state == "greeting":
            return "Hello! Are you looking to buy or lease a car today?", "get_intent"

        elif state == "get_intent":
            if "buy" in message.lower() or "lease" in message.lower():
                user_info["purchase_type"] = "buy" if "buy" in message.lower() else "lease"
                return "What type of vehicle are you interested in? (e.g., Sedan, SUV, Truck, or Van)", "get_vehicle_type"
            return "Please specify if you want to buy or lease a vehicle.", state

        elif state == "get_vehicle_type":
            vehicle_type = next(
                (vtype for vtype in ["sedan", "suv", "truck", "van"] if vtype in message.lower()),
                None
            )
            if vehicle_type:
                user_info["vehicle_type"] = vehicle_type
                return f"Great choice! What's your budget range?", "get_budget"
            return "Please specify the type of vehicle (Sedan, SUV, Truck, or Van).", state

        # Add other state handling logic here
        return "I'm not sure how to proceed. Can you clarify?", "greeting"
