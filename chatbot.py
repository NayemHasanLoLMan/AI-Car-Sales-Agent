import openai
import json
from dataclasses import dataclass, asdict
from typing import Optional, Dict
import os 

load_dotenv = ()

@dataclass
class CustomerInfo:
    # Personal Information
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    zip: Optional[str] = None

    # Car Type Selection
    car_condition: Optional[str] = None  # 'new' or 'pre-owned'
    transaction_type: Optional[str] = None  # 'buy' or 'lease'

    # Purchase Information (only for buying)
    payment_method: Optional[str] = None
    credit_rating: Optional[str] = None
    max_monthly_payment: Optional[str] = None
    max_down_payment: Optional[str] = None
    max_finance_term: Optional[str] = None

    # Lease Information (only for leasing)
    lease_term: Optional[str] = None
    annual_mileage: Optional[str] = None
    lease_down_payment: Optional[str] = None

    # Car Information
    car_type: Optional[str] = None
    make: Optional[str] = None
    year: Optional[str] = None
    model: Optional[str] = None
    max_mileage: Optional[str] = None  # Only for pre-owned cars
    desired_features: Optional[str] = None

    # Trade-in Information
    has_trade_in: Optional[bool] = None

    # Budget & Additional Information
    min_budget: Optional[str] = None
    max_budget: Optional[str] = None


class CarSalesGPTBot:
    def __init__(self, api_key, knowlage_base=None):
        openai.api_key = api_key
        self.knowlage_base = knowlage_base
        self.customer = CustomerInfo()
        self.conversation_history = []
        self.current_collection_phase = "personal_info"
        self.all_information_collected = False
        self.conversation_file = None
        self.required_fields = {
            'personal_info': ['first_name', 'last_name', 'email', 'phone', 'zip'],
            'budget': ['min_budget', 'max_budget', 'credit_rating'],
            'car_selection': ['car_condition', 'transaction_type'],
            'car_details': ['car_type', 'make', 'model', 'year', 'desired_features'],
            'trade_in': ['has_trade_in'],
            'transaction_details': []  # Will be populated based on transaction_type
        }

    def update_required_fields(self):
        """Update only transaction_details based on current state, ensuring correct logic for new vs pre-owned cars."""
        transaction_type = self.customer.transaction_type
        car_condition = self.customer.car_condition

        # If the car is pre-owned, force transaction type to 'buy'
        if car_condition == 'pre-owned':
            self.customer.transaction_type = 'buy'
            transaction_type = 'buy'

        # Ensure mutual exclusivity between buy and lease options
        if transaction_type == 'buy':
            self.required_fields['transaction_details'] = [
                'payment_method',
                'max_monthly_payment',
                'max_down_payment',
                'max_finance_term'
            ]
            # Reset lease-related fields
            self.customer.lease_term = "N/A"
            self.customer.annual_mileage = "N/A"
            self.customer.lease_down_payment = "N/A"
        elif transaction_type == 'lease':
            self.required_fields['transaction_details'] = [
                'lease_term',
                'annual_mileage',
                'lease_down_payment'
            ]
            # Reset buy-related fields
            self.customer.payment_method = "N/A"
            self.customer.max_monthly_payment = "N/A"
            self.customer.max_down_payment = "N/A"
            self.customer.max_finance_term = "N/A"
        else:
            self.required_fields['transaction_details'] = []

    def get_missing_fields(self):
        """Return the list of missing fields that need to be collected, treating 'N/A' as a valid response."""
        current_fields = self.required_fields.get(self.current_collection_phase, [])
        return [
            field for field in current_fields
            if getattr(self.customer, field) in (None, "")  # Allow 'N/A' as valid
        ]

    def check_phase_completion(self):
        """Check if the current phase is complete and move to the next phase if needed, ensuring all phases are covered."""
        missing_fields = self.get_missing_fields()
        
        if not missing_fields:  # If no missing fields, move forward
            next_phase = self._get_next_phase()
            if next_phase:
                self.current_collection_phase = next_phase
                print(f"✅ Moving to next phase: {self.current_collection_phase}")
            else:
                self.all_information_collected = True
                print("✅ All phases completed successfully.")
            return False
        
        return False


    def _get_next_phase(self):
        """Get the next phase in the collection process."""
        phases = list(self.required_fields.keys())
        current_index = phases.index(self.current_collection_phase)
        if current_index < len(phases) - 1:
            return phases[current_index + 1]
        return None

    def process_message(self, user_message):
        """Process user message and update fields accordingly."""
        try:
            self.conversation_history.append({"role": "user", "content": user_message})
            extracted_info = self.extract_information(user_message)
            self.update_customer_info(extracted_info)
            self.update_required_fields()
            response = self.get_bot_response()
            self.conversation_history.append({"role": "assistant", "content": response})
            return response
        except Exception as e:
            error_msg = f"I apologize, but I encountered an error: {str(e)}"
            self.conversation_history.append({"role": "assistant", "content": error_msg})
            return error_msg
        




    def update_customer_info(self, extracted_info: Dict):
        """
        Update customer information with validated data, ensuring proper type conversion
        and handling of special values.
        """
        for field, value in extracted_info.items():
            if hasattr(self.customer, field):
                current_value = getattr(self.customer, field)
                
                # Special handling for trade-in boolean field
                if field == 'has_trade_in':
                    if isinstance(value, bool):
                        setattr(self.customer, field, value)
                    elif isinstance(value, str):
                        # Convert string responses to boolean
                        if value.lower() in ['yes', 'true', 'y', '1']:
                            setattr(self.customer, field, True)
                        elif value.lower() in ['no', 'false', 'n', '0']:
                            setattr(self.customer, field, False)
                    continue
                
                # Handle "N/A" values
                if isinstance(value, str) and value.lower() in ["no", "none", "i don't have any"]:
                    value = "N/A"
                
                # Handle numeric fields (budgets, payments, etc.)
                if field in ['min_budget', 'max_budget', 'max_monthly_payment', 'max_down_payment']:
                    try:
                        if isinstance(value, str):
                            # Remove currency symbols and convert k to thousands
                            value = value.replace('$', '').replace(',', '')
                            if 'k' in value.lower():
                                value = float(value.lower().replace('k', '')) * 1000
                            else:
                                value = float(value)
                    except (ValueError, TypeError):
                        continue
                
                # Only update if:
                # 1. The field is currently empty (None)
                # 2. The new value is different from current
                # 3. The new value is not "N/A"
                if value and (current_value is None or 
                             str(value).lower() != str(current_value).lower()) and value != "N/A":
                    setattr(self.customer, field, value)
                    print(f"Updated {field}: {value}")
        
        # After updating, check if we can move to next phase
        self.check_phase_completion()


    def get_bot_response(self):
        """Generate the bot's response with improved flow maintenance."""
        missing_fields = self.get_missing_fields()

        if not missing_fields:
            if not self.check_phase_completion():
                return "Thank you for providing all the details! If you have any further questions, feel free to ask."
            return self.handle_exit()

        next_field = missing_fields[0]

        collected_info = {
            'name': f"{self.customer.first_name} {self.customer.last_name}".strip(),
            'email': self.customer.email,
            'phone': self.customer.phone,
            'zip': self.customer.zip,
            'budget_details': {
                'min_budget': self.customer.min_budget,
                'max_budget': self.customer.max_budget,
                'credit_rating': self.customer.credit_rating
            },
            'car_selection': {
                'car_condition': self.customer.car_condition,
                'transaction_type': self.customer.transaction_type
            },
            'car_details': {
                'make': self.customer.make,
                'model': self.customer.model,
                'type': self.customer.car_type,
                'year': self.customer.year,
                'desired_features': self.customer.desired_features,
                'max_mileage': self.customer.max_mileage,  
            },
            'trade_in': {
                'has_trade_in': self.customer.has_trade_in
            },
            'transaction_details': {
                'payment_method': self.customer.payment_method,
                'max_monthly_payment': self.customer.max_monthly_payment,
                'max_down_payment': self.customer.max_down_payment,
                'max_finance_term': self.customer.max_finance_term,
                'lease_term': self.customer.lease_term,
                'annual_mileage': self.customer.annual_mileage,
                'lease_down_payment': self.customer.lease_down_payment
            },
            'current_phase': self.current_collection_phase
        }

        system_prompt = f"""
        You are a professional car sales assistant helping a customer find their ideal car. Your goal is to collect all necessary information efficiently while maintaining a professional conversation flow. if user wants any information about the company provide information from the `knowlage_base`  file. for collecting information follow the `collected_info`and ask question to all collect information one by one. provide answer in proper dropdown and markdown format.

        knowlage_base:
        {self.knowlage_base}

        Current phase: {self.current_collection_phase}
        Next required field: {next_field}

        Already collected information:
        {json.dumps(collected_info, indent=2)}

        **Rules for Interaction**:
        1. Ask specifically for the next missing field: {next_field}
        2. If asking for zip code, specify it should be 5 digits
        3. If asking for budget, ask for specific numbers
        4. If asking for credit rating, list all the valid options (e.g., `Excellent`, `Very Good`, `Good`, `Fair`, `Poor`)
        5. If asking for car condition, allow only 'new' or 'pre-owned' options
        6. If asking for transaction type, allow only 'buy' or 'lease'
        7. If car is pre-owned, transaction type must be 'buy' (not 'lease')
        8. If asking about trade-in, confirm whether the user has a trade-in vehicle
        9. Maintain a natural conversation flow
        10. Reference previously collected information when relevant
        11. Be polite
        12. Keep responses concise, short and to the point.
        13. When a phase is complete, automatically move to the next set of questions
        14. Don't end the conversation until all phases and necessary questions in the phases are covered:
            - `personal_info`
            - `budget`
            - `car_selection`
            - `car_details`
            - `trade_in`
            - `transaction_details`
        15. Make sure to ask all nacessary question and collect information form `transaction_details`.


        **Make Sure**:
        - if contextually necessary then use the user's name otherwise avoid it.
        - Always ask the next question immediately after the user responds.
        - If the user provides incomplete information, politely ask for clarification.


        **Response Format**:
        Always structure your responses using proper markdown:
        1. Use **bold** for emphasis and important information
        2. Use bullet points (`•`) for lists
        3. Use `code formatting` for specific values or options
        4. Use ### for section headers if needed
        5. Use > for important quotes or highlights
        6. Use proper spacing and line breaks for readability
        7. Use --- for separating different sections if necessary
        8. End with a clear, focused question about the next required field
        """

        response = openai.ChatCompletion.create(
            model="gpt-4",
            temperature=1.0,
            top_p=0.9,
            max_tokens=3800,
            messages=[{"role": "system", "content": system_prompt},
                    *self.conversation_history]
        )
        return response.choices[0].message.content



    def extract_information(self, text):
        """Extract relevant information from customer message with improved validation."""
        try:
            name_context = ""
            if self.customer.first_name or self.customer.last_name:
                name_context = f"""
                Current name information:
                - First name: {self.customer.first_name}
                - Last name: {self.customer.last_name}
                """
            extraction_prompt = f"""
            Extract the relevant information from the customer message and return it as a valid JSON object.
            Current phase: {self.current_collection_phase}
            Current customer info: {json.dumps(asdict(self.customer), indent=2)}
            {name_context}

            Rules for extraction:
            1. For name handling:
                - If only one name is provided and we already have a first_name, treat it as last_name
                - If only one name is provided and we have no names yet, treat it as first_name
                - If full name is provided, split into first_name and last_name correctly

            2. IMPORTANT: Distinguish between different payment fields:
                - 'lease_down_payment': Only for lease transactions, represents initial payment for lease
                - 'max_budget': Overall maximum budget for purchase
                - 'max_down_payment': Down payment for purchase transactions

            3. Distinguishing Between `max_mileage` and `annual_mileage`
                `max_mileage` (Only for pre-owned cars)  
                - Represents the maximum acceptable mileage for a used car.  
                - Ensure this is extracted only when `car_condition` is "pre-owned".

                `annual_mileage`** (Only for leasing)  
                - Represents the expected annual mileage cap in a lease agreement.  
                - Ensure this is extracted only when `transaction_type` is "lease".

                Do NOT mix `max_mileage` and `annual_mileage`.  
                - Example: If the user says, "I want a used car with less than 50,000 miles", extract `max_mileage` = `"50000"`.
                - Example: If the user says, "I will drive about 12,000 miles per year", extract `annual_mileage` = `"12000"`.

            
            4. When in transaction_details phase and transaction_type is 'lease':
                - Any mentioned payment amount should be interpreted as 'lease_down_payment' or 'max_monthly_payment' based on which field is discussing.
                - Do not update 'max_budget' or other payment fields
                    
            5. Current transaction type is: {self.customer.transaction_type}
            
            6. Current collection phase is: {self.current_collection_phase}
            
            7. Ensure `car_condition` is either "new" or "pre-owned"
            
            8. Ensure `transaction_type` is either "buy" or "lease"
            
            9. Extract car details accurately, including `car_make`, `car_model`, `car_type` and `year`.
            
            10. Ensure `year` is a string between 1900 and 2025
            
            11. Ensure `zip` follows the 5-digit format (e.g., 12345)
            
            12. For credit_rating, normalize and map to one of these exact values:
                - "Excellent" for: excellent, perfect, outstanding, exceptional
                - "Very Good" for: very good, very well, great
                - "Good" for: good, okay, fine
                - "Fair" for: fair, average, moderate
                - "Poor" for: poor, bad, low

            If the user responds in a different format, extract and map it to the closest value based on the context. For example:
                - If the user says "it is good", extract and map it as **"Good"**.
                - If the user says "It's excellent", map it to **"Excellent"**.
                - Ensure that the output is a valid value from the list above and use the most appropriate match.
                
            13. Ensure budgets are numeric values
            
            14. For car_type use: "suv", "sedan", "truck", "van", or "coupe"
            
            15. For trade-in information, map common responses to True or False:
                - Normalize responses as follows:
                - **Positive responses** (e.g., "yes", "i have a trade-in", "trade-in available") → **True**
                - **Negative responses** (e.g., "no", "no trade-in", "i don't have a trade-in", "not interested in trade-in") → **False**
                - Handle all variations like "not sure", "maybe", or other ambiguous responses by prompting the user for a clearer answer.
                
            16. If the user does not provide a preference for any field (like last name, car model, etc.), set only that field to "N/A"(Don't change any other fields).
            
            17. Do not extract partial or incomplete information.
            
            18. Do not end conversation without extracting all the necessary information.
            
            19. Always ask the next question don't wait for user response.
            
            20. Understand the user intention to fill field based on the conversation history.

            Message: {text}

            Return a JSON object with only the newly extracted or updated information.
            """
            
            # Perform extraction through GPT-3
            response = openai.ChatCompletion.create(
                model="gpt-4",
                temperature=0.7,
                top_p=0.9,
                max_tokens=4000,
                messages=[{"role": "system", "content": "You are a precise data extraction assistant. Understand the user input and Extract only the specified information and return it as JSON."},
                        {"role": "user", "content": extraction_prompt}]
            )

            response_content = response.choices[0].message.content.strip()
            print(f"Raw response content: {response_content}")  
            
            # Treat the response content as a string first
            response_content_str = response_content.replace("```json", "").replace("```", "").strip()
            
            # Attempt to parse the string as JSON
            try:
                extracted_info = json.loads(response_content_str)
            except json.JSONDecodeError:
                # If parsing fails, treat the entire content as a string and wrap it in a JSON object
                extracted_info = {"raw_response": response_content_str}

            # Handle trade-in response (ensure normalization)
            if "has_trade_in" in extracted_info:
                trade_in_value = extracted_info["has_trade_in"]
                if isinstance(trade_in_value, str):
                    # Normalize responses to True/False
                    if any(word in trade_in_value.lower() for word in ["yes", "have", "available", "trade-in"]):
                        extracted_info["has_trade_in"] = True
                    elif any(word in trade_in_value.lower() for word in ["no", "don't", "none", "not"]):
                        extracted_info["has_trade_in"] = False
                    else:
                        extracted_info.pop("has_trade_in")
                elif not isinstance(trade_in_value, bool):
                    extracted_info.pop("has_trade_in")

            
            # Validate zip code if present
            if "zip" in extracted_info:
                zip_code = str(extracted_info["zip"])
                if not (len(zip_code) == 5 and zip_code.isdigit()):
                    extracted_info.pop("zip")

            # Validate year if present
            if "year" in extracted_info:
                year = str(extracted_info["year"])
                if not (year.isdigit() and 1900 <= int(year) <= 2025):
                    extracted_info.pop("year")

            # Ensure budget values are numeric
            for budget_field in ["min_budget", "max_budget"]:
                if budget_field in extracted_info:
                    try:
                        extracted_info[budget_field] = float(str(extracted_info[budget_field]).replace("k", "000"))
                    except (ValueError, TypeError):
                        extracted_info.pop(budget_field)

            return extracted_info

        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            return {}
        except Exception as e:
            print(f"Warning: Information extraction failed: {e}")
            return {}


    def generate_summary(self):
        """Generate a comprehensive summary of the conversation and customer requirements for dealership.""" 
        try:
            # Extract key conversation points from the conversation history
            conversation_extract = ""
            if self.conversation_history:
                conversation_extract = "Conversation Highlights:\n"
                for msg in self.conversation_history:
                    if msg.get('role') == 'user' and len(msg.get('content', '')) > 10:
                        conversation_extract += f"- Customer mentioned: {msg.get('content')}\n"
            
            # Include customer info if available
            customer_info = ""
            if hasattr(self, 'customer') and self.customer:
                customer_info = f"Customer Information: {json.dumps(asdict(self.customer), indent=2)}"
            
            summary_prompt = f"""
            **Task**: Generate a professional and actionable summary of the customer interaction for a car sales professional.

            **Customer Details**:
            {customer_info}

            **Conversation Context**:
            {conversation_extract}

            **Instructions**:
            1. **Focus on Key Information**:
            - Highlight the customer's preferences, requirements, and constraints.
            - Include only verified details from the conversation and customer information.
            - Exclude assumptions, placeholder content, or speculative language.

            2. **Structure the Summary**:
            - Start with a brief overview of the customer's profile (e.g., name, contact info, location).
            - Summarize the customer's car preferences (e.g., make, model, year, condition).
            - Outline the customer's budget and financial parameters (e.g., min/max budget, credit rating).
            - Mention any trade-in details or special requirements (e.g., desired features, lease vs. buy).
            - End with actionable insights for the sales team.

            3. **Tone and Style**:
            - Use a formal, professional, and concise tone.
            - Avoid repeating information unnecessarily.
            - Use bullet points or short paragraphs for clarity.

            4. **Avoid**:
            - Speculative language (e.g., "The customer might be interested in...").
            - Unverified or incomplete information.
            - Overly verbose or repetitive content.

            **Now, generate the summary based on the provided data**:
            """

            response = openai.ChatCompletion.create(
                model="gpt-4",
                temperature=0.7,
                top_p=0.9,
                max_tokens=1000,
                messages=[
                    {"role": "system", "content": "You are a professional car sales assistant. Create a concise and actionable summary of the customer interaction."},
                    {"role": "user", "content": summary_prompt}
                ]
            )

            # Extract the summary text from the response
            summary = response.choices[0].message.content
            return summary  # Return plain text, not a dictionary

        except Exception as e:
            return f"Error generating summary: {str(e)}"
        



    def generate_summary_to_file(self):
        """Generate a summary and save it to a separate text file.""" 
        try:
            summary = self.generate_summary()
            # summary_file = f"conversation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            # with open(summary_file, 'w', encoding='utf-8') as f:
            #     f.write(summary)
            return summary
        except Exception as e:
            return f"Error generating summary text file: {str(e)}"
        


    def handle_exit(self):
        """Handle conversation exit with summary generation.""" 
        if not self.all_information_collected:
            incomplete_fields = self.get_missing_fields()
            summary = f"""
            Conversation ended before all information was collected.
            Missing information: {', '.join(incomplete_fields)}
            """
            return summary
        else:
            summary = self.generate_summary()

        self.generate_summary_to_file()
        return """Thank you for your time. Here's a summary of our conversation:\n\n{summary}\n\nSummary file saved to 
        {summary_file}\n\nGoodbye!"""
    

def generate_customer_data(user_message, api_key=None, conversation_history=None, knowlage_base=None):
    # Use default API key if none provided
    if not api_key:
        api_key = "Api-Key"  # Replace

    # Initialize bot
    bot = CarSalesGPTBot(api_key, knowlage_base)
 
    # Load previous conversation history if provided
    if conversation_history:
        bot.conversation_history = conversation_history

    try:
        # Process the message
        response = bot.process_message(user_message)
        
        # Check if conversation is complete
        is_complete = bot.all_information_collected
        
        # Get customer info and filter out empty fields
        customer_data = asdict(bot.customer)
        filled_fields = {
            key: value for key, value in customer_data.items() 
            if value is not None and value != "" and value != "N/A"
        }
       
        # Return the response and current state
        return {
            'response': response,
            'customer_info': filled_fields,
            'is_complete': is_complete,
            'current_phase': bot.current_collection_phase
        }

    except Exception as e:
        return {
            'error': str(e),
            'is_complete': False,
            'current_phase': bot.current_collection_phase
        }



def generate_conversation_summary(conversation_data=None, api_key=None):
    """
    Generate a comprehensive conversation summary using both customer information and conversation history.
    
    Args:
        conversation_data (dict): Dictionary containing customer_info and conversation_history
        api_key (str): OpenAI API key
        
    Returns:
        str: The conversation summary as plain text
    """
    if not api_key:
        api_key = "api key"  # Replace with your actual API key
    
    bot = CarSalesGPTBot(api_key)
    
    # Check if conversation_data contains both customer info and messages
    if isinstance(conversation_data, dict):
        # Extract customer info if present
        if 'customer_info' in conversation_data:
            customer_info = conversation_data['customer_info']
            
            # Populate the customer object
            for field, value in customer_info.items():
                if hasattr(bot.customer, field):
                    setattr(bot.customer, field, value)
        
        # Set conversation history if available
        if 'conversation_history' in conversation_data:
            bot.conversation_history = conversation_data['conversation_history']
    
    # Generate the summary using both sources of information
    summary = bot.generate_summary()
    
    # Return the summary as plain text
    return summary


if __name__ == "__main__":
    conversation_history = []
    while True:
        try:
            user_input = input('You: ').strip()
            
            # Check for exit command
            if user_input.lower() in ['/exit']:
                # Generate final summary using generate_conversation_summary
                summary_result = generate_conversation_summary(conversation_history)
                print("\nGenerating conversation summary...")
                print("\nConversation Summary:")
                print(summary_result['conversation_summary'])
                break
                
            # Check for empty input
            if not user_input:
                print("Car Sales Assistant: I didn't catch that. Could you please repeat?")
                continue
                
            # Process message and store in history
            data = generate_customer_data(user_message=user_input, conversation_history=conversation_history)
            conversation_history.append({"role": "user", "content": user_input})
            if 'response' in data:
                conversation_history.append({"role": "assistant", "content": data['response']})
            print(data)
            
        except Exception as e:
            print(f"An error occurred: {e}")
