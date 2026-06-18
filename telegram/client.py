import os
import sys

from colorama import Fore
from telethon import TelegramClient
from telethon.sessions import StringSession

from config.settings import AppConfig
from utils.logger import get_logger

logger = get_logger()


def get_session(config: AppConfig):
    """Returns either a StringSession or a file path session based on config."""
    if config.string_session:
        return StringSession(config.string_session)

    # Ensure sessions directory exists or just save in root
    session_dir = ".sessions"
    os.makedirs(session_dir, exist_ok=True)
    return os.path.join(session_dir, "forwarder")


async def create_telegram_client(config: AppConfig, run_auth: bool = True) -> TelegramClient:
    """
    Initializes the TelegramClient.
    Connects to Telegram, and triggers terminal-based interactive auth if necessary.
    """
    session = get_session(config)
    client = TelegramClient(session, config.api_id, config.api_hash)

    try:
        await client.connect()
    except Exception as e:
        logger.error(f"Failed to connect to Telegram API: {e}")
        raise e

    if not await client.is_user_authorized():
        if not run_auth:
            raise RuntimeError("Not authenticated")
        logger.info("Client is not authorized. Starting authentication wizard...")
        try:
            print(f"\n{Fore.CYAN}--- Telegram Authorization ---")
            print("Please enter your phone number in international format.")
            print("Example: +12345678900 (include the '+' and your country code)")
            raw_phone = input("Enter Phone Number: ").strip()
            import re

            sanitized_phone = re.sub(r"[^\d+]", "", raw_phone)

            from telethon.errors import PhoneNumberInvalidError

            try:
                await client.start(phone=sanitized_phone)
            except PhoneNumberInvalidError:
                print(f"\n{Fore.RED}❌ Invalid Phone Number\n")
                print("The phone number you entered is invalid or not recognized by Telegram.")
                print("Please ensure you include the '+' and your country code.")
                print("Example: +12345678900\n")
                sys.exit(1)
        except KeyboardInterrupt:
            logger.warning("Auth cancelled by user.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise e

    me = await client.get_me()
    logger.info(
        f"Successfully authenticated as {me.first_name} (ID: {me.id}, Username: @{me.username or 'N/A'})"
    )
    return client


async def test_telegram_connection(config: AppConfig) -> bool:
    """
    Tests connection and credentials.
    Prints out connection success/failure.
    Returns True if authentication succeeded.
    """
    try:
        session = get_session(config)
        async with TelegramClient(session, config.api_id, config.api_hash) as client:
            me = await client.get_me()
            logger.info("--- Connection Test Success ---")
            logger.info("Connected to Telegram API successfully!")
            logger.info(f"Logged in as: {me.first_name} (@{me.username or 'none'})")

            # If using a file session, output a new string session in case they want it for headless environments
            if not config.string_session:
                string_session_str = StringSession.save(client.session)
                logger.info(
                    "\n--- String Session Generated (For Headless/Docker/Heroku environments) ---"
                )
                logger.info(string_session_str)
                logger.info(
                    "--------------------------------------------------------------------------\n"
                )
            return True
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False
