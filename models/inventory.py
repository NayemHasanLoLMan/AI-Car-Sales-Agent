class CarInventory:
    def __init__(self):
        self.inventory = {
            "sedan": {
                "economy": [
                    {
                        "name": "Toyota Camry",
                        "price": 25000,
                        "lease": 300,
                        "features": ["Bluetooth", "Backup Camera", "Lane Departure Warning"],
                        "deals": ["0% APR for 60 months", "$1500 cash back", "Free maintenance for 2 years"]
                    },
                    {
                        "name": "Honda Accord",
                        "price": 26000,
                        "lease": 320,
                        "features": ["Adaptive Cruise Control", "Apple CarPlay", "Blind Spot Monitor"],
                        "deals": ["1.9% APR for 72 months", "$2000 cash back", "No payments for 90 days"]
                    }
                ],
                "luxury": [
                    {
                        "name": "BMW 3 Series",
                        "price": 42000,
                        "lease": 550,
                        "features": ["Leather Seats", "Sunroof", "Premium Sound System"],
                        "deals": ["2.9% APR for 36 months", "First 3 payments waived", "Complimentary maintenance package"]
                    }
                ]
            },
            "suv": {
                "economy": [
                    {
                        "name": "Toyota RAV4",
                        "price": 28000,
                        "lease": 350,
                        "features": ["All-Wheel Drive", "Lane Assist", "Safety Sense 2.0"],
                        "deals": ["1.9% APR for 60 months", "$2500 cash back", "Free winter tire package"]
                    }
                ],
                "luxury": [
                    {
                        "name": "Lexus RX",
                        "price": 50000,
                        "lease": 600,
                        "features": ["Premium Sound System", "Navigation", "Leather Interior"],
                        "deals": ["1.9% APR luxury financing", "Complimentary maintenance", "Lease loyalty bonus"]
                    }
                ]
            }
        }

    def get_vehicles(self, vehicle_type: str, budget_category: str):
        return self.inventory.get(vehicle_type, {}).get(budget_category, [])

    def get_vehicle_details(self, vehicle_name: str):
        for category in self.inventory.values():
            for budget, vehicles in category.items():
                for vehicle in vehicles:
                    if vehicle_name.lower() in vehicle["name"].lower():
                        return vehicle
        return None