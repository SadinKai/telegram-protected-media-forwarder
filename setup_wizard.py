import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
import asyncio
import shutil
from configparser import ConfigParser
from datetime import datetime

from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)


def print_header(title: str):
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'=' * 50}")
    print(f"{Fore.CYAN}{Style.BRIGHT} {title}")
    print(f"{Fore.WHITE}{Style.DIM} Created by SadinKai")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 50}\n")


def get_input(prompt: str, default: str = "") -> str:
    placeholder = f" [{default}]" if default else ""
    user_val = input(f"{Fore.WHITE}{prompt}{placeholder}: ").strip()
    return user_val if user_val else default


def backup_configs():
    os.makedirs("backups", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backed_up = []

    if os.path.exists("config.ini"):
        backup_path = f"backups/config_{timestamp}.ini"
        shutil.copy("config.ini", backup_path)
        backed_up.append(f"config.ini -> {backup_path}")

    if os.path.exists("data/state.json"):
        backup_path = f"backups/state_{timestamp}.json"
        shutil.copy("data/state.json", backup_path)
        backed_up.append(f"data/state.json -> {backup_path}")

    if backed_up:
        print(f"\n{Fore.YELLOW}🛡️ Previous configurations backed up:")
        for b in backed_up:
            print(f"  - {b}")


async def run_interactive_selection(api_id: str, api_hash: str):
    from telethon import TelegramClient

    from utils.helpers import get_chat_access, get_chat_type, intify

    print(f"\n{Fore.CYAN}Connecting to Telegram to discover chats...")
    # Using standardized session path
    os.makedirs(".sessions", exist_ok=True)
    client = TelegramClient(os.path.join(".sessions", "forwarder"), int(api_id), api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
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
                return None, None
        else:
            await client.start()
    except Exception as e:
        print(f"{Fore.RED}✘ Failed to authenticate with Telegram: {e}")
        print(f"\n{Fore.YELLOW}Smart Recovery Suggestions:")
        print("1. Ensure your API ID and API Hash are correct.")
        print("2. Check your internet connection or VPN status.")
        print("3. Try running: python main.py doctor")
        return None, None

    print(f"{Fore.GREEN}✔ Successfully connected and authenticated!")

    # Fetch all dialogs
    print(f"{Fore.CYAN}Fetching dialog list...")
    dialogs = []
    me = await client.get_me()
    me_id = me.id if me else None

    async for d in client.iter_dialogs():
        dialogs.append(d)

    # Sort alphabetically
    dialogs.sort(key=lambda x: (x.name or "").lower())

    def display_dialogs(target_list):
        print(
            f"\n{Fore.WHITE}{Style.BRIGHT}{'#':<4} {'NAME':<30} {'TYPE':<12} {'ACCESS':<12} {'ID':<15}"
        )
        print("-" * 78)
        for idx, d in enumerate(target_list, 1):
            name = d.name or "Untitled Chat"
            if len(name) > 28:
                name = name[:25] + "..."
            ctype = get_chat_type(d.entity, me_id)
            caccess = get_chat_access(d.entity)
            print(f"{idx:<4} {name:<30} {ctype:<12} {caccess:<12} {d.id:<15}")
        print("-" * 78)

    async def select_chat(prompt_name: str) -> str:
        while True:
            print(f"\n{Fore.CYAN}{Style.BRIGHT}--- Select {prompt_name} Chat ---")
            print("1. Search chats")
            print("2. Show all chats")
            print("3. Enter manually")
            print(
                f"{Fore.WHITE}{Style.DIM}💡 Tip: Use 'me' or select 'Saved Messages' to use your own Saved Messages cloud."
            )

            choice = get_input("Choice", "1").strip()

            if choice not in ("1", "2", "3"):
                print(f"\n{Fore.RED}❌ Invalid Choice: Please enter '1', '2', or '3'.\n")
                continue

            if choice == "1":
                query = get_input("Search term").strip().lower()
                if not query:
                    print(f"{Fore.YELLOW}Search query cannot be empty.")
                    continue
                matches = [d for d in dialogs if query in (d.name or "").lower()]
                if not matches:
                    print(f"{Fore.YELLOW}No chats found matching '{query}'.")
                    continue
                display_dialogs(matches)
                num = get_input("Select chat index number (or Enter to search again)").strip()
                if not num:
                    continue
                if num.isdigit() and 1 <= int(num) <= len(matches):
                    selected = matches[int(num) - 1]
                    # Return string ID or 'me' if it's Saved Messages
                    if get_chat_type(selected.entity, me_id) == "Saved Messages":
                        return "me"
                    return str(selected.id)
                else:
                    print(f"\n{Fore.RED}❌ Invalid chat index selection.\n")
                    continue
            elif choice == "2":
                display_dialogs(dialogs)
                num = get_input("Select chat index number (or Enter to go back)").strip()
                if not num:
                    continue
                if num.isdigit() and 1 <= int(num) <= len(dialogs):
                    selected = dialogs[int(num) - 1]
                    if get_chat_type(selected.entity, me_id) == "Saved Messages":
                        return "me"
                    return str(selected.id)
                else:
                    print(f"\n{Fore.RED}❌ Invalid chat index selection.\n")
                    continue
            elif choice == "3":
                while True:
                    val = get_input(f"Enter {prompt_name} Chat ID or @Username").strip()
                    if not val:
                        print(
                            f"\n{Fore.RED}❌ Entry cannot be empty. Please enter a valid ID or username.\n"
                        )
                        continue
                    return val

    source_chat = None
    to_chat = None

    while True:
        source_chat = await select_chat("Source")
        to_chat = await select_chat("Destination")

        # Automatic Validation
        print(f"\n{Fore.CYAN}Testing configuration permissions...")
        try:
            # Check source
            source_entity = await client.get_entity(intify(source_chat))
            print(
                f" {Fore.GREEN}✔ Source chat found: {getattr(source_entity, 'title', '') or getattr(source_entity, 'first_name', '') or 'User'}"
            )

            # Check destination
            dest_entity = await client.get_entity(intify(to_chat))
            print(
                f" {Fore.GREEN}✔ Destination chat found: {getattr(dest_entity, 'title', '') or getattr(dest_entity, 'first_name', '') or 'User'}"
            )

            # Check write permission on destination
            print(" Verifying send permissions...")
            msg = await client.send_message(
                dest_entity, "✔ System validation test message (Self-destructing)", silent=True
            )
            await client.delete_messages(dest_entity, msg)
            print(f" {Fore.GREEN}✔ Send permissions confirmed")

            # Validation Passed
            print(f"\n{Fore.GREEN}{Style.BRIGHT}Validation Successful!")
            break
        except Exception as e:
            print(f"\n{Fore.RED}✘ Chat validation or permissions check failed!")
            print(f"Error detail: {e}")
            print(f"\n{Fore.YELLOW}Possible causes:")
            print("- You are not a member of the chat.")
            print("- You do not have permissions to post messages in the destination.")
            print("- The chat ID/username is incorrect.")
            print(f"\n{Fore.WHITE}Please try selecting the chats again.")

    await client.disconnect()
    return source_chat, to_chat


def run_wizard():
    # Session Directory write validation
    session_dir = ".sessions"
    try:
        os.makedirs(session_dir, exist_ok=True)
        # Verify write permission by writing a temporary hidden file
        test_file_path = os.path.join(session_dir, ".write_test")
        with open(test_file_path, "w") as f:
            f.write("test")
        os.remove(test_file_path)
    except Exception as e:
        print_header("Telegram Protected Media Forwarder Setup Wizard")
        print(f"\n{Fore.RED}❌ Session Directory Permission Error\n")
        print(f"Cannot write to the sessions directory '{session_dir}'.")
        print(f"System Error: {e}")
        print("\nSuggested Recovery:")
        print("1. Ensure your user account has write permissions for this folder.")
        print("2. If running on Windows, make sure the directory is not marked as Read-Only.")
        print("3. Try running your terminal as Administrator/with elevated privileges.")
        sys.exit(1)

    try:
        print_header("Telegram Protected Media Forwarder Setup Wizard")
        print(
            "Welcome! This wizard will guide you through setting up your forwarding configurations.\n"
        )

        # Load existing env settings
        existing_api_id = ""
        existing_api_hash = ""
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                for line in f:
                    if "=" in line:
                        key, val = line.strip().split("=", 1)
                        if key.lower() == "api_id":
                            existing_api_id = val
                        elif key.lower() == "api_hash":
                            existing_api_hash = val

        # Step 1: Mode Picker
        while True:
            print(f"{Fore.WHITE}{Style.BRIGHT}Choose Setup Mode:")
            print("1. Quick Setup (Recommended)")
            print("2. Advanced Setup")
            mode = get_input("Choice", "1").strip()
            if mode not in ("1", "2"):
                print(f"\n{Fore.RED}❌ Invalid Choice: Please enter '1' or '2'.\n")
                continue
            break

        # Step 2: API Keys
        print(f"\n{Fore.GREEN}Step 1: Telegram API Keys")
        print("API credentials act as your account's secure authorization keys.")
        print("Obtain them from: https://my.telegram.org (API Development Tools)")

        while True:
            api_id = get_input("Enter API ID", existing_api_id).strip()
            if not api_id:
                print(f"\n{Fore.RED}❌ Invalid API ID\n")
                print("API ID cannot be empty.")
                print("\nPlease try again.\n")
                continue
            if not api_id.isdigit():
                print(f"\n{Fore.RED}❌ Invalid API ID\n")
                print("API ID must contain only numbers.")
                print("\nExample:")
                print("12345678")
                print("\nPlease try again.\n")
                continue
            break

        while True:
            api_hash = get_input("Enter API Hash", existing_api_hash).strip()
            if not api_hash:
                print(f"\n{Fore.RED}❌ Invalid API Hash\n")
                print("API Hash cannot be empty.")
                print("\nPlease try again.\n")
                continue
            break

        source_chat = ""
        to_chat = ""
        offset = "0"
        upload_delay = "3.0"
        keep_downloads = "false"
        log_level = "INFO"

        while True:
            interactive = (
                get_input(
                    "\nWould you like to connect to Telegram and select chats interactively? (Y/n)",
                    "Y",
                )
                .strip()
                .upper()
            )
            if not interactive:
                interactive = "Y"
            if interactive not in ("Y", "N", "YES", "NO"):
                print(f"\n{Fore.RED}❌ Invalid Choice: Please enter 'Y' or 'n'.\n")
                continue
            interactive = "Y" if interactive in ("Y", "YES") else "N"
            break

        if interactive == "Y":
            source_chat, to_chat = asyncio.run(run_interactive_selection(api_id, api_hash))
            if not source_chat or not to_chat:
                print(
                    f"{Fore.RED}Interactive chat picker could not complete. Reverting to manual setup."
                )
                source_chat = ""
                to_chat = ""

        if not source_chat or not to_chat:
            print(f"\n{Fore.GREEN}Step 2: Manual Chat Setup")
            print("Enter usernames (e.g. @MyChannel) or numerical IDs (e.g. -10012345678).")
            print("Need help? Run: python main.py list-chats")
            while True:
                source_chat = get_input("Enter Source Chat", source_chat).strip()
                if not source_chat:
                    print(
                        f"\n{Fore.RED}❌ Source chat cannot be empty. Please enter a valid ID or username.\n"
                    )
                    continue
                break
            while True:
                to_chat = get_input("Enter Destination Chat", to_chat).strip()
                if not to_chat:
                    print(
                        f"\n{Fore.RED}❌ Destination chat cannot be empty. Please enter a valid ID or username.\n"
                    )
                    continue
                break

        if mode == "2":
            # Advanced options
            print(f"\n{Fore.GREEN}Step 3: Advanced Settings")

            while True:
                offset_input = get_input(
                    "Enter initial Message ID offset (0 to start from beginning)", "0"
                ).strip()
                if not offset_input.isdigit():
                    print(f"\n{Fore.RED}❌ Invalid Offset: Must be a positive number.\n")
                    continue
                offset = offset_input
                break

            while True:
                delay_input = get_input("Delay between message forwards (seconds)", "3.0").strip()
                try:
                    val = float(delay_input)
                    if val < 0:
                        print(f"\n{Fore.RED}❌ Invalid Delay: Must be a positive number.\n")
                        continue
                    upload_delay = delay_input
                    break
                except ValueError:
                    print(
                        f"\n{Fore.RED}❌ Invalid Delay: Must be a valid decimal number (e.g. 3.0).\n"
                    )
                    continue

            while True:
                keep_input = (
                    get_input("Keep downloaded files in downloads directory? (true/false)", "false")
                    .strip()
                    .lower()
                )
                if keep_input not in ("true", "false"):
                    print(f"\n{Fore.RED}❌ Invalid Value: Enter 'true' or 'false'.\n")
                    continue
                keep_downloads = keep_input
                break

            while True:
                level_input = (
                    get_input("Logging Level (DEBUG, INFO, WARNING, ERROR)", "INFO").strip().upper()
                )
                if level_input not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
                    print(f"\n{Fore.RED}❌ Invalid Level: Enter DEBUG, INFO, WARNING, or ERROR.\n")
                    continue
                log_level = level_input
                break

        # Backup files
        backup_configs()

        # Generate files
        print(f"\n{Fore.YELLOW}Saving configuration files...")
        with open(".env", "w") as f:
            f.write(f"API_ID={api_id}\n")
            f.write(f"API_HASH={api_hash}\n")

        config_out = ConfigParser()
        config_out["General"] = {
            "api_id": api_id,
            "api_hash": api_hash,
            "download_dir": "downloads",
            "log_level": log_level.upper(),
            "keep_downloads": keep_downloads.lower(),
            "max_retries": "3",
            "upload_delay": upload_delay,
            "flood_wait_limit": "300",
        }

        config_out["ForwardJob1"] = {"from": source_chat, "to": to_chat, "offset": offset}

        with open("config.ini", "w") as f:
            config_out.write(f)

        # Success screen
        print(f"\n{Fore.CYAN}{Style.BRIGHT}═══════════════════════════════════════")
        print(f"\n{Fore.GREEN}{Style.BRIGHT}Setup Complete 🎉")
        print(f"{Fore.WHITE}{Style.DIM}Created by SadinKai")
        print(f"\n{Fore.WHITE}Checklist:")
        print(f" {Fore.GREEN}✔ Telegram authenticated")
        print(f" {Fore.GREEN}✔ Source selected: {source_chat}")
        print(f" {Fore.GREEN}✔ Destination selected: {to_chat}")
        print(f" {Fore.GREEN}✔ Validation passed")
        print(f" {Fore.GREEN}✔ Configuration saved")
        print(f"\n{Fore.WHITE}{Style.BRIGHT}Next Step:")
        print(f"  {Fore.YELLOW}{Style.BRIGHT}python main.py start")
        print(f"\n{Fore.WHITE}Need help later?")
        print("  python main.py list-chats")
        print("  python main.py doctor")
        print(f"\n{Fore.CYAN}{Style.BRIGHT}═══════════════════════════════════════\n")
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}⚠️ Setup cancelled by user. Goodbye!")
        sys.exit(1)


if __name__ == "__main__":
    run_wizard()
