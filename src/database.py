import sqlite3
from datetime import datetime, date
import os
from typing import Optional, List, Dict, Any

class Database:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'calories.db')
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def init_db(self):
        """Initialize the database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    reminder_enabled INTEGER DEFAULT 1,
                    daily_target INTEGER DEFAULT 2000
                )
            ''')
            
            # Create meals table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS meals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    food_name TEXT NOT NULL,
                    calories REAL NOT NULL,
                    meal_type TEXT NOT NULL,
                    photo_url TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Create daily_logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    total_calories REAL NOT NULL,
                    target_met INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            conn.commit()

    def create_user(self, user_id: int, username: str) -> None:
        """Create a new user in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR IGNORE INTO users (user_id, username, created_at) VALUES (?, ?, ?)',
                (user_id, username, datetime.utcnow().isoformat())
            )
            conn.commit()

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_meal(self, user_id: int, food_name: str, calories: float, meal_type: str, photo_url: str = None) -> None:
        """Add a new meal entry."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO meals (user_id, food_name, calories, meal_type, photo_url, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, food_name, calories, meal_type, photo_url, datetime.utcnow().isoformat())
            )
            conn.commit()

    def get_daily_meals(self, user_id: int, day: date = None) -> List[Dict[str, Any]]:
        """Get all meals for a specific day."""
        if day is None:
            day = date.today()
        
        start_date = f"{day.isoformat()}T00:00:00"
        end_date = f"{day.isoformat()}T23:59:59"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT * FROM meals 
                   WHERE user_id = ? AND created_at BETWEEN ? AND ?
                   ORDER BY created_at''',
                (user_id, start_date, end_date)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_daily_total(self, user_id: int, day: date = None) -> float:
        """Calculate total calories for a specific day."""
        meals = self.get_daily_meals(user_id, day)
        return sum(meal["calories"] for meal in meals)

    def update_settings(self, user_id: int, settings: dict) -> None:
        """Update user settings."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            updates = []
            params = []
            for key, value in settings.items():
                updates.append(f"{key} = ?")
                params.append(value)
            params.append(user_id)
            
            query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
            cursor.execute(query, params)
            conn.commit()

    def log_daily_summary(self, user_id: int, total_calories: float, target_met: bool) -> None:
        """Log daily calorie summary."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO daily_logs 
                   (user_id, date, total_calories, target_met, created_at)
                   VALUES (?, ?, ?, ?, ?)''',
                (user_id, date.today().isoformat(), total_calories, 
                 1 if target_met else 0, datetime.utcnow().isoformat())
            )
            conn.commit()

# Initialize database connection
db = Database() 