import os
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from functools import lru_cache
import time

load_dotenv()

class FoodRecognition:
    def __init__(self):
        self.api_key = os.getenv("FOOD_API_KEY")
        self.base_url = "https://api.calorieninjas.com/v1/nutrition"
        self.headers = {
            'X-Api-Key': self.api_key,
            'Content-Type': 'application/json'
        }
        self.cache = {}
        self.cache_timeout = 3600  # 1 hour cache

    def process_image(self, image_data: bytes) -> tuple[str, float]:
        """
        Process the image and return the recognized food and its calories.
        Optimized version with basic image analysis.
        """
        try:
            image = Image.open(BytesIO(image_data))
            width, height = image.size
            
            if width < 100 or height < 100:
                return None, "Image too small"

            # Quick image analysis for common colors
            # This is a simple optimization to avoid always returning "apple"
            image = image.resize((100, 100))  # Reduce size for faster processing
            colors = image.convert('RGB').getcolors(10000)
            
            # Simple color-based food matching
            if colors:
                dominant_colors = sorted(colors, key=lambda x: x[0], reverse=True)[:3]
                avg_color = tuple(sum(c[1][i] for c in dominant_colors) // 3 for i in range(3))
                
                # Very basic color matching
                if avg_color[0] > 150 and avg_color[1] < 100 and avg_color[2] < 100:
                    query = "apple"  # Red foods
                elif avg_color[1] > 150 and avg_color[0] < 100:
                    query = "lettuce"  # Green foods
                elif avg_color[2] > 150:
                    query = "blueberry"  # Blue/Purple foods
                elif all(c > 200 for c in avg_color):
                    query = "rice"  # White foods
                elif all(c < 100 for c in avg_color):
                    query = "chocolate"  # Dark foods
                else:
                    query = "mixed_food"
            else:
                query = "mixed_food"

            return self.get_food_calories(query)
            
        except Exception as e:
            return None, f"Error processing image: {str(e)}"

    @lru_cache(maxsize=100)
    def get_food_calories(self, query: str) -> tuple[str, float]:
        """Get calorie information for a food item with caching."""
        # Check internal cache first
        cache_key = query.lower()
        current_time = time.time()
        
        if cache_key in self.cache:
            timestamp, data = self.cache[cache_key]
            if current_time - timestamp < self.cache_timeout:
                return data

        try:
            response = requests.get(
                self.base_url,
                headers=self.headers,
                params={'query': query},
                timeout=5  # Add timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    item = data['items'][0]
                    result = (item['name'], item['calories'])
                    # Update cache
                    self.cache[cache_key] = (current_time, result)
                    return result
                return None, "Food not found in database"
            else:
                return None, f"API Error: {response.status_code}"
                
        except requests.Timeout:
            return None, "API request timed out"
        except Exception as e:
            return None, f"Error getting calories: {str(e)}"

    def estimate_portion_size(self, image_data: bytes) -> float:
        """Estimate portion size from image - optimized version."""
        try:
            image = Image.open(BytesIO(image_data))
            # Basic size-based estimation
            width, height = image.size
            area = width * height
            
            # Very basic portion estimation based on image size
            if area > 1000000:  # Large image
                return 1.5
            elif area < 250000:  # Small image
                return 0.75
            return 1.0
            
        except:
            return 1.0  # Default fallback

# Initialize food recognition service
food_recognition = FoodRecognition() 