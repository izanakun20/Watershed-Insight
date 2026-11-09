import os
import json
import base64
import requests
from typing import Dict, Any, Tuple
from dotenv import load_dotenv

load_dotenv()

class AIService:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8080", 
            "X-Title": "SIH 26015 Watershed Command Centre",
            "Content-Type": "application/json"
        }
        self.vision_model = "openai/gpt-4o-mini"  # Reliable vision support via OpenRouter
        self.text_model = "openai/gpt-4o-mini"      # Fast, affordable text model for advisory

    def classify_image(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> Tuple[str, str, str]:
        """
        Takes an uploaded image of a field intervention and returns (intervention_type, confidence, short_description).
        Does NOT use self-reported data.
        """
        if not self.api_key:
            return "Unknown (AI Disabled)", "0.0", "AI Disabled"

        prompt = """
        You are an expert watershed management AI. Inspect this field photo and classify the intervention type.
        Choose ONE of the following types: 
        - Check Dam
        - Farm Pond
        - Stop Dam
        - Trenching
        - Afforestation
        - Percolation Tank
        - Contour Bunding
        - Gully Plugs
        - Terracing
        - Pasture Development
        - Agro-forestry
        - Other

        Respond strictly in JSON format without markdown wrapping, like this:
        {
            "intervention_type": "Check Dam",
            "confidence": "0.85",
            "short_description": "A masonry check dam built across a stream to harvest water."
        }
        """
        
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        image_url = f"data:{mime_type};base64,{base64_image}"

        payload = {
            "model": self.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
        }

        try:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            text = result["choices"][0]["message"]["content"].strip()
            
            # Clean up markdown if model didn't respect response_format completely
            if text.startswith("```json"):
                text = text[7:-3]
            elif text.startswith("```"):
                text = text[3:-3]
                
            data = json.loads(text.strip())
            return (
                data.get("intervention_type", "Unknown"), 
                str(data.get("confidence", "0.0")),
                data.get("short_description", "No description provided.")
            )
            
        except Exception as e:
            print(f"AI Classification Error: {e}")
            return "Classification Failed", "0.0", f"Error connecting to OpenRouter: {e}"


    def generate_advisory(self, evidence_data: Dict[str, Any]) -> str:
        """
        Generates a concise advisory report based strictly on the provided computed evidence.
        """
        if not self.api_key:
            return "AI Advisory Disabled. Please configure OPENROUTER_API_KEY."

        prompt = f"""
        You are an expert watershed management advisory AI.
        Generate a concise, factual advisory report based ONLY on the following computed GIS evidence and cross-check data.
        DO NOT invent statistics, scores, or claims. Do not say the satellite 'proves' anything.
        Use terms like 'evidence suggests', 'inconclusive', or 'field verification recommended'.
        Keep the report to 2 short paragraphs.
        
        Computed Evidence:
        {json.dumps(evidence_data, indent=2)}
        """

        payload = {
            "model": self.text_model,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        try:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=self.headers, json=payload, timeout=20)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"AI Advisory Error: {e}")
            return f"Advisory generation failed due to an error: {e}"

ai_service = AIService()
