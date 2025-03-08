import os
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

class FoodRecognition:
    def __init__(self):
        self.api_key = os.getenv("FOOD_API_KEY")
        self.base_url = "https://api.calorieninjas.com/v1/nutrition"
        self.headers = {
            'X-Api-Key': self.api_key,
            'Content-Type': 'application/json'
        }

    def process_image(self, image_data: bytes) -> tuple[str, float]:
        """
        Process the image and return the recognized food and its calories.
        For this implementation, we'll use a simplified approach where we
        use CalorieNinjas API with the most likely food item.
        
        In a production environment, you would want to use a more sophisticated
        image recognition API like Google Cloud Vision or Azure Computer Vision.
        """
        try:
            # For demo purposes, we'll use a simplified approach
            # In reality, you'd want to use proper image recognition here
            image = Image.open(BytesIO(image_data))
            # Get image dimensions for basic validation
            width, height = image.size
            if width < 100 or height < 100:
                return None, "Image too small"

            # For demo, we'll just query a default food item
            # In production, this would be replaced with actual image recognition
            query = "apple"  # Default query for demonstration
            return self.get_food_calories(query)
            
        except Exception as e:
            return None, f"Error processing image: {str(e)}"

    def get_food_calories(self, query: str) -> tuple[str, float]:
        """Get calorie information for a food item."""
        try:
            response = requests.get(
                self.base_url,
                headers=self.headers,
                params={'query': query}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    item = data['items'][0]
                    return item['name'], item['calories']
                return None, "Food not found in database"
            else:
                return None, f"API Error: {response.status_code}"
                
        except Exception as e:
            return None, f"Error getting calories: {str(e)}"

    def estimate_portion_size(self, image_data: bytes) -> float:
        """
        Estimate portion size from image.
        This is a placeholder function - in a real implementation,
        you would use computer vision to estimate portion size.
        """
        # For demo purposes, return a default multiplier
        return 1.0

# Initialize food recognition service
food_recognition = FoodRecognition() 