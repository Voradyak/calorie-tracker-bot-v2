from datetime import datetime, time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from database import db

class SchedulerService:
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = BackgroundScheduler()
        self.setup_jobs()

    def setup_jobs(self):
        """Setup scheduled jobs."""
        # Daily summary at midnight (00:00)
        self.scheduler.add_job(
            self.send_daily_summary,
            CronTrigger(hour=0, minute=0),
            id='daily_summary'
        )
        
        # Meal logging reminder at 23:00
        self.scheduler.add_job(
            self.send_reminder,
            CronTrigger(hour=23, minute=0),
            id='meal_reminder'
        )

    def start(self):
        """Start the scheduler."""
        self.scheduler.start()

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()

    async def send_daily_summary(self):
        """Send daily calorie summary to all users."""
        try:
            # Get all users
            users = db.supabase.table("users").select("*").execute()
            
            for user in users.data:
                if not user.get('user_id'):
                    continue
                
                # Calculate total calories for the day
                total_calories = db.get_daily_total(user['user_id'])
                target_met = total_calories <= user.get('daily_target', 2000)
                
                # Create summary message
                message = (
                    f"📊 Daily Calorie Summary\n\n"
                    f"Total calories consumed: {total_calories:.1f}\n"
                    f"Daily target: {user.get('daily_target', 2000)}\n"
                    f"Status: {'✅ Target met!' if target_met else '⚠️ Target exceeded'}"
                )
                
                # Log the summary
                db.log_daily_summary(
                    user['user_id'],
                    total_calories,
                    target_met
                )
                
                # Send message to user
                await self.bot.send_message(
                    chat_id=user['user_id'],
                    text=message
                )
                
        except Exception as e:
            print(f"Error sending daily summary: {str(e)}")

    async def send_reminder(self):
        """Send reminder to users who haven't logged all meals."""
        try:
            # Get all users with reminders enabled
            users = db.supabase.table("users") \
                .select("*") \
                .eq("reminder_enabled", True) \
                .execute()
            
            for user in users.data:
                if not user.get('user_id'):
                    continue
                
                # Check if user has logged any meals today
                meals = db.get_daily_meals(user['user_id'])
                if not meals.data:
                    message = (
                        "🔔 Reminder!\n\n"
                        "You haven't logged any meals today. "
                        "Don't forget to track your food intake!\n\n"
                        "Use /add to log manually or send a photo of your food."
                    )
                    
                    # Send reminder
                    await self.bot.send_message(
                        chat_id=user['user_id'],
                        text=message
                    )
                    
        except Exception as e:
            print(f"Error sending reminder: {str(e)}")

# Note: The scheduler instance will be created in main.py
# when the bot is initialized 