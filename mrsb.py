import httpx
import logging
import random
import json
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
from functools import wraps
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define your admin user IDs
ADMINS = [2129865779]  # Replace with your real admin user IDs

# Path to the configuration file
CONFIG_FILE_PATH = 'file.txt'

def read_config() -> str:
    """Read configuration from file with proper formatting."""
    if not os.path.exists(CONFIG_FILE_PATH):
        return "Configuration file not found."
    
    try:
        with open(CONFIG_FILE_PATH, 'r') as file:
            return file.read()
    except IOError as e:
        logger.error(f"Failed to read config file: {e}")
        return "Error reading configuration file."


def write_config(content: str) -> None:
    """Write new configuration to file with proper formatting."""
    with open(CONFIG_FILE_PATH, 'w') as file:
        file.write(content.strip())  # Strip leading/trailing whitespace

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("WarpGeneratorNG")

FALLBACK_BASE_KEYS = [
    "7HZp2d69-G92K6Bz8-7yO9So85",
    "94lB36du-4960HEzs-68E5jd3I",
    "28R1r9iF-6Li9Kq27-U514Yx8l",
    "k18ba35e-5whgj679-8Pi34nI2",
    "0P18xF5J-5Ww637Le-016bHqT5",
    "2F05CD1P-7CJ0g2I5-B3hO4b56",
    "68y15EAJ-C3519JfR-zve6847x",
    "7I8n60ds-Chy26D57-5W21IFH8",
    "U4C071LW-JhT604K8-3a6s27uT",
    "aAsQ1072-fy983J0c-r432m6ZG",
]

WARP_CLIENT_HEADERS = {
    "CF-Client-Version": "a-6.11-2223",
    "Host": "api.cloudflareclient.com",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
    "User-Agent": "okhttp/3.12.1",
}

def get_auth_headers(token: str) -> dict:
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": f"Bearer {token}",
    }

def get_auth_headers_get(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

class User:
    def __init__(self, user_id: str, license_code: str, token: str) -> None:
        self.user_id = user_id
        self.license_code = license_code
        self.token = token

class GenerateResults:
    def __init__(self, account_type: str, referral_count: int, license_code: str) -> None:
        self.account_type = account_type
        self.referral_count = referral_count
        self.license_code = license_code

    def __repr__(self) -> str:
        return f"WarpGenerateResults(account_type={self.account_type}, referral_count={self.referral_count}, license_code={self.license_code})"

def register_single() -> User:
    logger.debug("Start registering new account")
    client = httpx.Client(
        base_url="https://api.cloudflareclient.com/v0a2223",
        headers=WARP_CLIENT_HEADERS,
        timeout=30,
    )
    response = client.post("/reg").json()
    client.close()
    user_id = response["id"]
    license_code = response["account"]["license"]
    token = response["token"]
    return User(user_id=user_id, license_code=license_code, token=token)

def generate_key(base_key: str) -> GenerateResults:
    logger.debug("Start generating new key")
    client = httpx.Client(
        base_url="https://api.cloudflareclient.com/v0a2223",
        headers=WARP_CLIENT_HEADERS,
        timeout=30,
    )
    try:
        user1 = register_single()
        user2 = register_single()

        client.patch(
            f"/reg/{user1.user_id}",
            headers=get_auth_headers(user1.token),
            json={"referrer": user2.user_id},
        )
        client.delete(f"/reg/{user2.user_id}", headers=get_auth_headers_get(user2.token))
        client.put(
            f"/reg/{user1.user_id}/account",
            headers=get_auth_headers(user1.token),
            json={"license": base_key},
        )
        client.put(
            f"/reg/{user1.user_id}/account",
            headers=get_auth_headers(user1.token),
            json={"license": user1.license_code},
        )
        response = client.get(
            f"/reg/{user1.user_id}/account", headers=get_auth_headers_get(user1.token)
        ).json()
        
        account_type = response.get("account_type", "Unknown")
        referral_count = response.get("referral_count", 0)
        license_code = response.get("license", "Unknown")
        
        logger.debug(f"API Response: {response}")

    except httpx.HTTPStatusError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        raise
    except Exception as err:
        logger.error(f"Other error occurred: {err}")
        raise
    finally:
        client.close()

    return GenerateResults(
        account_type=account_type,
        referral_count=referral_count,
        license_code=license_code,
    )


def validate_base_key(key: str) -> bool:
    return len(key) == 26 and key.count('-') == 2

def generate_warp_key(update: Update, context: CallbackContext) -> None:
    """Generate WARP key and send it as a message with delete button."""
    if update.message:
        initial_message = update.message.reply_text("Generating WARP key, please wait...", parse_mode='Markdown')
    elif update.callback_query:
        update.callback_query.answer("Generating WARP key...")
        initial_message = update.callback_query.message.reply_text("Generating WARP key, please wait...", parse_mode='Markdown')
    else:
        logger.error("update is not a message or callback query")
        return

    try:
        base_key = random.choice(FALLBACK_BASE_KEYS)
        result = generate_key(base_key)

        # Check if the key generation was successful
        if result.referral_count > 0 and result.license_code:
            key_info = {'Quota': result.referral_count, 'license': result.license_code}
            message = (
                "**🎉 Warp+ Key Generated! 🎉**\n"
                f"**Quota:** `{key_info['Quota']}` GiB\n"
                f"**License Key:** `{key_info['license']}`"
            )
            keyboard = [
                [InlineKeyboardButton("Delete", callback_data='delete_key')]
            ]
        else:
            message = f"No key available to display. Referral count: {result.referral_count}, Quota: {result.referral_count}"
            keyboard = [
                [InlineKeyboardButton("Generate Again", callback_data='generate_key')]
            ]

    except Exception as e:
        message = f"Failed to generate key: {str(e)}"
        keyboard = []

    if update.message:
        initial_message.edit_text(message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        initial_message.edit_text(message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))


def notify_admin_new_user(user_id: str, user_name: str, context: CallbackContext) -> None:
    """Notify admin about a new user."""
    admin_chat_id = ADMINS[0]  # Replace with the appropriate admin chat ID
    message = (f"**New User Alert!**\n"
               f"**User ID:** `{user_id}`\n"
               f"**User Name:** `{user_name}`")
    try:
        context.bot.send_message(chat_id=admin_chat_id, text=message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Failed to notify admin about new user {user_id}: {e}")

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

def start(update: Update, context: CallbackContext) -> None:
    """Handle /start command."""
    if update.message:
        user = update.message.from_user
        user_id = str(user.id)
        user_name = user.first_name
        
        # Save the user ID for future broadcasts
        save_user_id(user_id)
        
        # Notify admin about the new user
        notify_admin_new_user(user_id, user_name, context)
        
        # Create an inline keyboard with "Generate WARP Key", "Config VPN", and "Show Trusted Sellers" buttons
        keyboard = [
            [InlineKeyboardButton("Generate WARP Key", callback_data='generate_key')],
            [InlineKeyboardButton("Config VPN", callback_data='show_config')],
            [InlineKeyboardButton("Show Trusted Sellers", callback_data='show_trusted_sellers')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            f"User Id: `{user_id}`\n\nHello `{user.first_name}`👋, Welcome to the Bot.\n-\nAuthor: @gassturn",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        logger.error("update.message is None in /start handler")


def config(update: Update, context: CallbackContext) -> None:
    """Handle /config command."""
    if update.message:
        config_message = read_config()
        keyboard = [
            [InlineKeyboardButton("Generate WARP Key", callback_data='generate_key')],
            [InlineKeyboardButton("Share Feedback", url='https://t.me/secretbipion'), InlineKeyboardButton("More Info", url='https://t.me/configpion')],
            [InlineKeyboardButton("Delete", callback_data='delete_key')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(config_message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        logger.error("update.message is None in /config handler")


def admin_only(func):
    """Decorator to ensure only admins can use certain commands."""
    @wraps(func)
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        if update.message:
            user_id = update.message.from_user.id
            if user_id in ADMINS:
                return func(update, context, *args, **kwargs)
            else:
                update.message.reply_text("Sorry, you don't have permission to use this command.")
        else:
            logger.error("update.message is None in admin_only decorator")
    return wrapper

@admin_only
def update_config(update: Update, context: CallbackContext) -> None:
    """Update the configuration file with the provided content and pin the message."""
    if update.message:
        new_config = ' '.join(context.args).replace('\\n', '\n')
        
        if not new_config:
            update.message.reply_text("Please provide the new configuration text.")
            return
        
        write_config(new_config)
        
        sent_message = update.message.reply_text("Configuration updated successfully. Here is the updated config: /config", parse_mode='Markdown')
        
        chat_id = update.message.chat_id
        context.bot.pin_chat_message(chat_id=chat_id, message_id=sent_message.message_id)
    else:
        logger.error("update.message is None in /update_config handler")

@admin_only
def update_trusted_sellers(update: Update, context: CallbackContext) -> None:
    """Update the list of trusted sellers from provided text."""
    if update.message:
        # Combine context.args into a single string with new lines
        new_sellers_list = ' '.join(context.args)
        
        if not new_sellers_list:
            update.message.reply_text("Please provide the new list of trusted sellers.")
            return
        
        # Write to seller.txt, preserving new lines
        with open('seller.txt', 'w') as file:
            file.write(new_sellers_list)
        
        update.message.reply_text("Trusted sellers list updated successfully.")
    else:
        logger.error("update.message is None in /update_trusted_sellers handler")


USER_IDS_FILE = 'user_ids.txt'

def load_user_ids() -> set:
    """Load user IDs from file."""
    if os.path.exists(USER_IDS_FILE):
        with open(USER_IDS_FILE, 'r') as file:
            return set(line.strip() for line in file)
    return set()

def save_user_id(user_id: str) -> None:
    """Save a new user ID to the file."""
    with open(USER_IDS_FILE, 'a') as file:
        file.write(f"{user_id}\n")

@admin_only
def broadcast(update: Update, context: CallbackContext) -> None:
    """Broadcast a message or media to all users."""
    if update.message:
        # Check if there's an image or other media attached
        if update.message.photo:
            media_file_id = update.message.photo[-1].file_id
            media_type = 'photo'
        elif update.message.document:
            media_file_id = update.message.document.file_id
            media_type = 'document'
        else:
            media_type = 'text'
            media_file_id = ' '.join(context.args)  # For text messages
        
        user_ids = load_user_ids()
        for user_id in user_ids:
            try:
                if media_type == 'photo':
                    context.bot.send_photo(chat_id=user_id, photo=media_file_id)
                elif media_type == 'document':
                    context.bot.send_document(chat_id=user_id, document=media_file_id)
                else:
                    context.bot.send_message(chat_id=user_id, text=media_file_id)
            except Exception as e:
                logger.error(f"Failed to send {media_type} to {user_id}: {e}")
        
        update.message.reply_text(f"{media_type.capitalize()} broadcasted to {len(user_ids)} users.")
    else:
        logger.error("update.message is None in /broadcast handler")


def read_sellers_list() -> str:
    """Read the list of trusted sellers from a file."""
    sellers_file_path = 'seller.txt'
    if not os.path.exists(sellers_file_path):
        return "Trusted sellers file not found."
    
    with open(sellers_file_path, 'r') as file:
        return file.read()

def trusted_sellers(update: Update, context: CallbackContext) -> None:
    """Handle /trusted_sellers command and send the list of trusted sellers with a delete button."""
    if update.message:
        sellers_list = read_sellers_list()
        keyboard = [
            [InlineKeyboardButton("Delete", callback_data='delete_trusted_sellers')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(sellers_list, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        logger.error("update.message is None in /trusted_sellers handler")


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import CallbackContext
import os

def button(update: Update, context: CallbackContext) -> None:
    """Handle button presses."""
    query = update.callback_query
    if query:
        user_id = query.from_user.id
        callback_data = query.data  # Extract callback data once

        # Define the Back to Menu button
        back_to_menu_button = InlineKeyboardButton("Back to Menu", callback_data='back_to_menu')

        if callback_data == 'generate_key':
            generate_warp_key(update, context)
            query.answer()  # Acknowledge the callback
        elif callback_data == 'show_config':
            # Create keyboard for configuration options
            config_keyboard = [
                [InlineKeyboardButton("Config By RNG_TEAM", callback_data='rng')],
                [InlineKeyboardButton("Config By PakyaVpn", callback_data='pakya'), InlineKeyboardButton("Config By Dxni", callback_data='dani')],
                [back_to_menu_button]
            ]
            reply_markup = InlineKeyboardMarkup(config_keyboard)
            
            query.edit_message_text(
                text="Select your VPN configuration:",
                reply_markup=reply_markup
            )
            query.answer()  # Acknowledge the callback
        elif callback_data == 'pakya':
            # Handle "Button Pakya" choice
            file_path = 'pakya.txt'
            if os.path.exists(file_path):
                with open(file_path, 'r') as file:
                    file_contents = file.read()
                
                keyboard = [
                    [back_to_menu_button]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.message.reply_text(
                    text="Config By @anakjati567:\n" + file_contents,
                    reply_markup=reply_markup
                )
            else:
                keyboard = [
                    [back_to_menu_button]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.message.reply_text(
                    text="The file 'file.txt' does not exist.",
                    reply_markup=reply_markup
                )
            query.answer()  # Acknowledge the callback
        elif callback_data == 'rng':
            # Handle "Button Pakya" choice
            file_path = 'rng.txt'
            if os.path.exists(file_path):
                with open(file_path, 'r') as file:
                    file_contents = file.read()
                
                keyboard = [
                    [back_to_menu_button]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.message.reply_text(
                    text="Config By RNG_TEAM:\n" + file_contents,
                    reply_markup=reply_markup
                )
            else:
                keyboard = [
                    [back_to_menu_button]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.message.reply_text(
                    text="The file 'file.txt' does not exist.",
                    reply_markup=reply_markup
                )
            query.answer()  # Acknowledge the callback
        elif callback_data == 'dani':
            # Handle "Button Dani" choice
            file_path = 'dani.txt'
            if os.path.exists(file_path):
                with open(file_path, 'r') as file:
                    file_contents = file.read()
                
                keyboard = [
                    [back_to_menu_button]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.message.reply_text(
                    text="Config By @dnbizowner:\n" + file_contents,
                    reply_markup=reply_markup
                )
            else:
                keyboard = [
                    [back_to_menu_button]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.message.reply_text(
                    text="The file 'file.txt' does not exist.",
                    reply_markup=reply_markup
                )
            query.answer()  # Acknowledge the callback
        elif callback_data == 'show_trusted_sellers':
            sellers_list = read_sellers_list()
            keyboard = [
                [InlineKeyboardButton("Delete", callback_data='delete_trusted_sellers')],
                [back_to_menu_button]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.message.edit_text(sellers_list, parse_mode='Markdown', reply_markup=reply_markup)
            query.answer()  # Acknowledge the callback
        elif callback_data == 'delete_key':
            if user_id in ADMINS:
                context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
                keyboard = [
                    [back_to_menu_button]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.message.reply_text(text="Message deleted.", reply_markup=reply_markup)
            else:
                query.answer("You don't have permission to use this button.")
        elif callback_data == 'delete_trusted_sellers':
            if user_id in ADMINS:
                context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
                keyboard = [
                    [back_to_menu_button]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.message.reply_text(text="Trusted sellers list deleted.", reply_markup=reply_markup)
            else:
                query.answer("You don't have permission to use this button.")
        elif callback_data == 'back_to_menu':
            # Create the main menu keyboard again
            main_menu_keyboard = [
                [InlineKeyboardButton("Generate WARP Key", callback_data='generate_key')],
                [InlineKeyboardButton("Config VPN", callback_data='show_config')],
                [InlineKeyboardButton("Show Trusted Sellers", callback_data='show_trusted_sellers')]
            ]
            reply_markup = InlineKeyboardMarkup(main_menu_keyboard)
            
            query.message.edit_text(
                text="Welcome back to the main menu. Please choose an option:",
                reply_markup=reply_markup
            )
            query.answer()  # Acknowledge the callback
        else:
            logger.error(f"Unknown callback data: {callback_data}")
            query.answer()  # Optionally acknowledge unknown callback data
    else:
        logger.error("update.callback_query is None in button handler")



def main():
    """Start the bot."""
    updater = Updater('7287462728:AAHZpXDQekc3r7uXETteSmoNpnS23OfodN0')  # Replace with your actual bot token
    
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    
    # Add handlers
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('config', config))
    dispatcher.add_handler(CommandHandler('trusted_sellers', trusted_sellers))
    dispatcher.add_handler(CommandHandler('update_trusted_sellers', update_trusted_sellers))
    dispatcher.add_handler(CommandHandler('broadcast', broadcast))  # Add the broadcast command handler
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(CommandHandler('update_config', update_config))
    
    # Start polling
    updater.start_polling()
    updater.idle()



if __name__ == '__main__':
    main()



