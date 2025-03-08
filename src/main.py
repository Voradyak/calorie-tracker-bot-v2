import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)
from dotenv import load_dotenv
from database import db
from food_recognition import food_recognition
from scheduler import SchedulerService

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
FOOD_NAME, CALORIES = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the bot and create user if not exists."""
    user = update.effective_user
    
    try:
        # Check if user exists
        existing_user = db.get_user(user.id)
        if not existing_user.data:
            # Create new user
            db.create_user(user.id, user.username or user.first_name)
            welcome_text = (
                f"Welcome to CalorieTracker Bot, {user.first_name}! 🎉\n\n"
                "I'll help you track your daily calorie intake.\n"
                "You can:\n"
                "📸 Send a photo of your food\n"
                "📝 Use /add to log manually\n"
                "📊 Use /summary to see your daily total\n"
                "⚙️ Use /settings to configure reminders"
            )
        else:
            welcome_text = (
                f"Welcome back, {user.first_name}! 🎉\n"
                "Ready to track your calories?\n"
                "Send a photo or use /add to get started!"
            )
        
        await update.message.reply_text(welcome_text)
        
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        await update.message.reply_text(
            "Sorry, there was an error starting the bot. Please try again later."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message."""
    help_text = (
        "🤖 CalorieTracker Bot Help\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/add - Manually add food and calories\n"
        "/summary - View today's calorie summary\n"
        "/settings - Configure your preferences\n"
        "/help - Show this help message\n\n"
        "📸 You can also send a photo of your food for automatic recognition!"
    )
    await update.message.reply_text(help_text)

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the manual food logging conversation."""
    await update.message.reply_text(
        "What food would you like to log? Please enter the name:"
    )
    return FOOD_NAME

async def food_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the food name and ask for calories."""
    context.user_data['food_name'] = update.message.text
    await update.message.reply_text(
        "How many calories does it contain? Please enter a number:"
    )
    return CALORIES

async def calories_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the calories and save the meal."""
    try:
        calories = float(update.message.text)
        food_name = context.user_data['food_name']
        
        # Add meal to database
        db.add_meal(
            user_id=update.effective_user.id,
            food_name=food_name,
            calories=calories,
            meal_type="manual"
        )
        
        # Get daily total
        daily_total = db.get_daily_total(update.effective_user.id)
        
        await update.message.reply_text(
            f"✅ Logged {food_name} ({calories} calories)\n"
            f"Daily total: {daily_total:.1f} calories"
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "Please enter a valid number for calories."
        )
        return CALORIES

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

async def process_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process food photo and estimate calories."""
    try:
        # Get the photo file
        photo = await update.message.photo[-1].get_file()
        photo_data = await photo.download_as_bytearray()
        
        # Process the image
        food_name, calories = food_recognition.process_image(photo_data)
        
        if food_name and calories:
            # Add meal to database
            db.add_meal(
                user_id=update.effective_user.id,
                food_name=food_name,
                calories=calories,
                meal_type="photo",
                photo_url=photo.file_path
            )
            
            # Get daily total
            daily_total = db.get_daily_total(update.effective_user.id)
            
            await update.message.reply_text(
                f"📸 Recognized: {food_name}\n"
                f"Estimated calories: {calories:.1f}\n"
                f"Daily total: {daily_total:.1f} calories"
            )
        else:
            await update.message.reply_text(
                "Sorry, I couldn't recognize the food in this image. "
                "Please try again or use /add to log manually."
            )
            
    except Exception as e:
        logger.error(f"Error processing photo: {str(e)}")
        await update.message.reply_text(
            "Sorry, there was an error processing your photo. "
            "Please try again or use /add to log manually."
        )

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show daily calorie summary."""
    try:
        user_id = update.effective_user.id
        user = db.get_user(user_id).data
        
        if not user:
            await update.message.reply_text(
                "Please use /start to set up your profile first."
            )
            return
            
        # Get daily meals and total
        meals = db.get_daily_meals(user_id)
        total_calories = db.get_daily_total(user_id)
        target = user.get('daily_target', 2000)
        
        # Create summary message
        summary_text = "📊 Today's Calorie Summary\n\n"
        
        if meals.data:
            for meal in meals.data:
                summary_text += (
                    f"🍽 {meal['food_name']}: {meal['calories']:.1f} calories\n"
                )
        else:
            summary_text += "No meals logged today\n"
            
        summary_text += f"\nTotal: {total_calories:.1f} / {target} calories"
        
        if total_calories > target:
            summary_text += "\n⚠️ Daily target exceeded!"
        
        await update.message.reply_text(summary_text)
        
    except Exception as e:
        logger.error(f"Error showing summary: {str(e)}")
        await update.message.reply_text(
            "Sorry, there was an error getting your summary. Please try again later."
        )

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show and modify user settings."""
    try:
        user = db.get_user(update.effective_user.id).data
        
        if not user:
            await update.message.reply_text(
                "Please use /start to set up your profile first."
            )
            return
            
        settings_text = (
            "⚙️ Your Settings\n\n"
            f"Daily calorie target: {user.get('daily_target', 2000)}\n"
            f"Reminders: {'Enabled' if user.get('reminder_enabled', True) else 'Disabled'}\n\n"
            "Use these commands to modify:\n"
            "/set_target <number> - Set daily calorie target\n"
            "/toggle_reminders - Enable/disable reminders"
        )
        
        await update.message.reply_text(settings_text)
        
    except Exception as e:
        logger.error(f"Error showing settings: {str(e)}")
        await update.message.reply_text(
            "Sorry, there was an error accessing your settings. Please try again later."
        )

async def set_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set daily calorie target."""
    try:
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text(
                "Please provide a valid number. Example: /set_target 2000"
            )
            return
            
        target = int(context.args[0])
        if target < 500 or target > 5000:
            await update.message.reply_text(
                "Please enter a reasonable daily target between 500 and 5000 calories."
            )
            return
            
        db.update_settings(
            update.effective_user.id,
            {"daily_target": target}
        )
        
        await update.message.reply_text(
            f"✅ Daily calorie target updated to {target} calories."
        )
        
    except Exception as e:
        logger.error(f"Error setting target: {str(e)}")
        await update.message.reply_text(
            "Sorry, there was an error updating your target. Please try again later."
        )

async def toggle_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle reminder settings."""
    try:
        user = db.get_user(update.effective_user.id).data
        current_setting = user.get('reminder_enabled', True)
        
        db.update_settings(
            update.effective_user.id,
            {"reminder_enabled": not current_setting}
        )
        
        status = "enabled" if not current_setting else "disabled"
        await update.message.reply_text(f"✅ Reminders {status}.")
        
    except Exception as e:
        logger.error(f"Error toggling reminders: {str(e)}")
        await update.message.reply_text(
            "Sorry, there was an error updating your reminder settings. "
            "Please try again later."
        )

def main() -> None:
    """Start the bot."""
    # Create application
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    
    # Create conversation handler for manual food logging
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_command)],
        states={
            FOOD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, food_name_received)],
            CALORIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, calories_received)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("summary", summary))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CommandHandler("set_target", set_target))
    application.add_handler(CommandHandler("toggle_reminders", toggle_reminders))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.PHOTO, process_photo))
    
    # Create and start scheduler
    scheduler = SchedulerService(application.bot)
    scheduler.start()
    
    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main() 