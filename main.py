import argparse
import asyncio
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
from colorama import Fore, Style, init

from config.settings import AppConfig, ConfigError, load_config
from services.forward_service import load_state, run_forward_jobs, save_state
from setup_wizard import run_wizard
from telegram.client import create_telegram_client, test_telegram_connection
from utils.helpers import get_chat_access, get_chat_type, intify
from utils.logger import get_logger, setup_logger

init(autoreset=True)


def show_banner():
    banner = f"""
{Fore.CYAN}{Style.BRIGHT}╔══════════════════════════════════════════════════════════════╗
║             TELEGRAM PROTECTED MEDIA FORWARDER               ║
║           Production-grade Media Migration CLI               ║
║                   Created by SadinKai                        ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def get_recovery_suggestions(error_type: str) -> str:
    suggestions = f"\n{Fore.YELLOW}Smart Recovery Suggestions:\n"
    if error_type == "connection":
        suggestions += (
            "✘ Telegram connection failed\n\n"
            "Possible causes:\n"
            "  * Telegram is blocked by your local network / ISP\n"
            "  * VPN is disconnected or unstable\n"
            "  * Invalid API credentials or session state\n\n"
            "Suggested actions:\n"
            "  1. Run: python main.py doctor\n"
            "  2. Test connection with a mobile hotspot\n"
            "  3. Verify your API credentials in config.ini or run: python main.py setup"
        )
    elif error_type == "credentials":
        suggestions += (
            "✘ API credentials verification failed\n\n"
            "Possible causes:\n"
            "  * API_ID or API_HASH are empty or incorrectly formatted\n"
            "  * Environment variables (.env) not loaded or mismatching config.ini\n\n"
            "Suggested actions:\n"
            "  1. Run: python main.py setup to recreate configs\n"
            "  2. Verify that API_ID is an integer and API_HASH is a 32-character hex string"
        )
    elif error_type == "state":
        suggestions += (
            "✘ State file registry access failed\n\n"
            "Possible causes:\n"
            "  * Permission denied on state file or directory\n"
            "  * The JSON file is corrupted or formatted incorrectly\n\n"
            "Suggested actions:\n"
            "  1. Run: python main.py reset-offset --all to re-initialize progress status\n"
            "  2. Check path permissions on: data/state.json"
        )
    elif error_type == "permissions":
        suggestions += (
            "✘ Destination chat posting restriction detected\n\n"
            "Possible causes:\n"
            "  * You are not a member of the destination group/channel\n"
            "  * You do not have permissions to post messages (e.g. read-only member)\n"
            "  * The destination chat ID or username does not exist\n\n"
            "Suggested actions:\n"
            "  1. Run: python main.py list-chats and verify the destination chat's ACCESS column says Read/Write\n"
            "  2. Confirm your account status inside Telegram directly"
        )
    else:
        suggestions += (
            "✘ System validation check encountered an error\n\n"
            "Suggested actions:\n"
            "  1. Run: python main.py doctor to diagnose all system modules"
        )
    return suggestions


def perform_health_check(config, is_doctor_cmd: bool = False) -> bool:
    print(
        f"\n{Fore.CYAN}{Style.BRIGHT}{'System Health Report' if is_doctor_cmd else 'System Validation Report'}"
    )
    print(f"{Fore.WHITE}{Style.DIM}Created by SadinKai\n")
    issues = 0
    remediations = []

    # 1. API Credentials Checks
    try:
        if not config.api_id or not config.api_hash:
            raise ConfigError("API_ID and API_HASH cannot be empty.")
        if len(config.api_hash) != 32:
            raise ConfigError("API_HASH must be exactly 32 characters long.")
        print(f" {Fore.GREEN}✔ API credentials")
    except Exception as e:
        issues += 1
        print(f" {Fore.RED}✘ API credentials valid")
        remediations.append(f"API credentials configuration invalid: {e}")
        remediations.append("Run: python main.py setup to configure your API ID and API Hash.")
        print_report_summary(issues, remediations)
        return False

    # 1.5. Forwarding Jobs Check
    if not config.jobs:
        issues += 1
        print(f" {Fore.RED}✘ Forwarding jobs configured")
        remediations.append(
            "No forwarding jobs defined. Run: python main.py setup to configure a forwarding job."
        )
    else:
        print(f" {Fore.GREEN}✔ Forwarding jobs configured")

    # 2. Session File
    session_file = os.path.join(".sessions", "forwarder.session")
    if os.path.exists(session_file):
        if not os.access(session_file, os.R_OK | os.W_OK):
            issues += 1
            print(f" {Fore.RED}✘ Session file")
            remediations.append(
                f"Fix permissions on {session_file} or delete it to authenticate again."
            )
        else:
            print(f" {Fore.GREEN}✔ Session file")
    else:
        print(f" {Fore.YELLOW}⚠ Session file (First run will generate session)")

    # 3. State File
    state_file = config.state_file_path
    state_dir = os.path.dirname(state_file)
    if state_dir and not os.path.exists(state_dir):
        try:
            os.makedirs(state_dir, exist_ok=True)
        except Exception:
            pass

    state_healthy = True
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                import json

                json.load(f)
        except Exception:
            state_healthy = False

    if state_healthy:
        print(f" {Fore.GREEN}✔ State file")
    else:
        issues += 1
        print(f" {Fore.RED}✘ State file")
        remediations.append(
            f"Registry file {state_file} is corrupted. Run: python main.py reset-offset --all to recreate."
        )

    # 4. Download Directory
    dl_dir = config.download_dir
    try:
        os.makedirs(dl_dir, exist_ok=True)
        # Test write capability
        test_file = os.path.join(dl_dir, ".doctor_write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        print(f" {Fore.GREEN}✔ Download directory")
    except Exception as e:
        issues += 1
        print(f" {Fore.RED}✘ Download directory")
        remediations.append(
            f"Download path is not writable: {os.path.abspath(dl_dir)}. Exception: {e}"
        )

    # 5. Telegram Network Connection & Chat Permissions Checks
    async def run_online_checks():
        nonlocal issues
        try:
            client = await create_telegram_client(config, run_auth=False)
            async with client:
                print(f" {Fore.GREEN}✔ Telegram connection")

                # Check source and destination chats for each job
                for idx, job in enumerate(config.jobs, 1):
                    # Source Chat Access
                    try:
                        source_entity = await client.get_entity(intify(job.from_chat))
                        print(
                            f" {Fore.GREEN}✔ Source chat access: Job {idx} ({getattr(source_entity, 'title', '') or getattr(source_entity, 'first_name', '') or 'User'})"
                        )
                    except Exception:
                        issues += 1
                        print(
                            f" {Fore.RED}✘ Source chat access: Job {idx} ({job.from_chat}) - Inaccessible"
                        )
                        remediations.append(
                            f"Confirm you are a member of the source chat: '{job.from_chat}'. Run list-chats to verify."
                        )

                    # Destination Chat Access & Permissions
                    try:
                        dest_entity = await client.get_entity(intify(job.to_chat))
                        print(
                            f" {Fore.GREEN}✔ Destination chat access: Job {idx} ({getattr(dest_entity, 'title', '') or getattr(dest_entity, 'first_name', '') or 'User'})"
                        )

                        try:
                            # Verify posting permissions
                            msg = await client.send_message(
                                dest_entity, "✔ System validation test message", silent=True
                            )
                            await client.delete_messages(dest_entity, msg)
                            print(f" {Fore.GREEN}✔ Destination send permissions: Job {idx}")
                        except Exception as e:
                            issues += 1
                            print(
                                f" {Fore.RED}✘ Destination send permissions: Job {idx} - Restricted"
                            )
                            remediations.append(
                                f"You do not have write/post permissions for destination chat: '{job.to_chat}'. Details: {e}"
                            )
                    except Exception as e:
                        issues += 1
                        print(
                            f" {Fore.RED}✘ Destination chat access: Job {idx} ({job.to_chat}) - Inaccessible"
                        )
                        remediations.append(
                            f"Verify chat '{job.to_chat}' exists and is accessible by your account. Details: {e}"
                        )
        except Exception as conn_err:
            issues += 1
            if str(conn_err) == "Not authenticated":
                print(f" {Fore.RED}✘ Not authenticated")
                remediations.append(
                    "Run:\n     python main.py setup\n\n     or\n\n     python main.py test-connection"
                )
            else:
                print(f" {Fore.RED}✘ Telegram connection")
                remediations.append(f"Connection/Authentication failed: {conn_err}")
            print(f" {Fore.RED}✘ Source chat access")
            print(f" {Fore.RED}✘ Destination chat access")
            print(f" {Fore.RED}✘ Destination send permissions")

    try:
        asyncio.run(run_online_checks())
    except Exception as run_err:
        issues += 1
        print(f" {Fore.RED}✘ Diagnostics execution interrupted: {run_err}")

    # Configuration valid status
    if issues == 0:
        print(f" {Fore.GREEN}✔ Configuration valid")
    else:
        print(f" {Fore.RED}✘ Configuration valid")

    print_report_summary(issues, remediations)
    return issues == 0


def print_report_summary(issues: int, remediations: list):
    print("\n" + "=" * 50)
    print(f"Issues Found: {issues}")
    if issues == 0:
        print(f"\n{Fore.GREEN}{Style.BRIGHT}System Ready 🚀")
    else:
        print(f"\n{Fore.YELLOW}Suggested Remediation Steps:")
        for idx, step in enumerate(remediations, 1):
            print(f"  {idx}. {step}")
    print("=" * 50 + "\n")


def cmd_validate(args):
    """Subcommand to validate configurations offline and online."""
    try:
        config = AppConfig()
        success = perform_health_check(config, is_doctor_cmd=False)
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}✘ Configuration/Validation Error: {e}")
        print(f"\n{Fore.YELLOW}Suggested recovery action:")
        print(
            "  1. Your 'config.ini' or '.env' file may be missing, malformed, or contain invalid values."
        )
        print("  2. Re-run the interactive setup to regenerate configurations:")
        print("     python main.py setup")
        sys.exit(1)


def cmd_doctor(args):
    """Subcommand to run full system diagnostics health check."""
    try:
        config = AppConfig()
        success = perform_health_check(config, is_doctor_cmd=True)
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}✘ Diagnostics/Configuration Error: {e}")
        print(f"\n{Fore.YELLOW}Suggested recovery action:")
        print(
            "  1. Your 'config.ini' or '.env' file may be missing, malformed, or contain invalid values."
        )
        print("  2. Re-run the interactive setup to regenerate configurations:")
        print("     python main.py setup")
        sys.exit(1)


def cmd_list_chats(args):
    """Subcommand to fetch and display dialog list."""
    try:
        config = AppConfig()
        if not config.api_id or not config.api_hash:
            raise ConfigError("API_ID and API_HASH are required to connect to Telegram.")
    except ConfigError as ce:
        print(f"{Fore.RED}Configuration Error: {ce}")
        print(get_recovery_suggestions("credentials"))
        sys.exit(1)

    async def run_list():
        print(f"{Fore.CYAN}Connecting to Telegram to discover chats...")
        client = await create_telegram_client(config)
        async with client:
            dialogs = []
            me = await client.get_me()
            me_id = me.id if me else None

            async for d in client.iter_dialogs():
                dialogs.append(d)

            # Filter matches if search parameter is set
            search_query = args.search
            if search_query:
                search_query = search_query.strip().lower()
                dialogs = [d for d in dialogs if search_query in (d.name or "").lower()]
                print(f"\nResults for search query: '{search_query}'\n")
            else:
                print("\nAvailable Telegram Chats\n")

            # Alphabetical sort
            dialogs.sort(key=lambda x: (x.name or "").lower())

            # Print table
            print(f"{Fore.WHITE}{Style.BRIGHT}{'NAME':<28} {'TYPE':<12} {'ACCESS':<12} {'ID':<15}")
            print("-" * 68)
            for d in dialogs:
                name = d.name or "Untitled Chat"
                if len(name) > 28:
                    name = name[:25] + "..."
                ctype = get_chat_type(d.entity, me_id)
                caccess = get_chat_access(d.entity)
                print(f"{name:<28} {ctype:<12} {caccess:<12} {d.id:<15}")
            print("-" * 68)
            print(f"Total Chats Found: {len(dialogs)}\n")

    try:
        asyncio.run(run_list())
    except Exception as e:
        print(f"{Fore.RED}Failed to list chats: {e}")
        print(get_recovery_suggestions("connection"))
        sys.exit(1)


def cmd_test_connection(args):
    """Subcommand to test Telegram API connection."""
    try:
        config = load_config()
        setup_logger(config.log_level)
        logger = get_logger()
        logger.info("Testing Telegram connection...")
        success = asyncio.run(test_telegram_connection(config))
        if success:
            print(f"\n{Fore.GREEN}✔ Connection test completed successfully!")
        else:
            print(f"\n{Fore.RED}✘ Connection test failed.")
            print(get_recovery_suggestions("connection"))
            sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}Error during connection test: {e}")
        print(get_recovery_suggestions("connection"))
        sys.exit(1)


def cmd_setup(args):
    """Subcommand to launch the interactive wizard."""
    run_wizard()


def cmd_start(args):
    """Subcommand to run the forwarding loop."""
    try:
        config = load_config()
        setup_logger(config.log_level)
        logger = get_logger()

        show_banner()
        print(f"{Fore.YELLOW}Press Ctrl+C at any time to safely stop the forwarder.\n")
        logger.info("Initializing Telegram client...")

        async def run_app():
            client = await create_telegram_client(config)
            async with client:
                await run_forward_jobs(client, config)

        asyncio.run(run_app())
    except ConfigError as ce:
        print(f"{Fore.RED}Configuration Error: {ce}")
        print("Please configure active forwarding jobs first: python main.py setup")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Application interrupted by user. Exiting.")
    except Exception as e:
        print(f"{Fore.RED}Critical unexpected error: {e}")
        print(get_recovery_suggestions("unknown"))
        sys.exit(1)


def cmd_status(args):
    """Subcommand to show configuration and current status of jobs."""
    try:
        config = load_config()
        state = load_state(config.state_file_path)

        show_banner()
        print(f"{Fore.CYAN}{Style.BRIGHT}--- Jobs Forwarding Status ---")

        if not config.jobs:
            print("No jobs configured.")
            return

        for idx, job in enumerate(config.jobs, 1):
            job_state = state.get(job.name, {})
            offset = job_state.get("offset", job.initial_offset)
            status = job_state.get("status", "idle")
            last_run = job_state.get("last_run", "Never")

            print(f"\n{Fore.WHITE}{Style.BRIGHT}{idx}. Job: '{job.name}'")
            print(f"   Source Chat:      {job.from_chat}")
            print(f"   Destination Chat: {job.to_chat}")
            print(f"   Current Offset ID: {Fore.GREEN}{offset}")
            print(f"   Execution Status:  {status.upper()}")
            print(f"   Last Active Run:  {last_run}")

    except ConfigError as ce:
        print(f"{Fore.RED}Configuration Error: {ce}")
        print(get_recovery_suggestions("credentials"))
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}Error retrieving job status: {e}")
        sys.exit(1)


def cmd_reset_offset(args):
    """Subcommand to reset offsets in state.json."""
    try:
        config = load_config()
        state_file = config.state_file_path
        state = load_state(state_file)

        if not args.job and not args.all:
            print(f"{Fore.RED}Error: You must specify a job with --job <name> or use --all.")
            return

        if args.all:
            confirm = (
                input(f"{Fore.YELLOW}Are you sure you want to reset offsets for ALL jobs? (y/N): ")
                .strip()
                .lower()
            )
            if confirm == "y":
                for job in config.jobs:
                    if job.name in state:
                        state[job.name]["offset"] = job.initial_offset
                        state[job.name]["status"] = "idle"
                save_state(state_file, state)
                print(f"{Fore.GREEN}✔ Offsets for all jobs reset to initial offsets successfully.")
            else:
                print("Operation cancelled.")
        else:
            job_name = args.job
            job_found = any(j.name == job_name for j in config.jobs)
            if not job_found:
                print(f"{Fore.RED}Error: Job '{job_name}' not found in configuration.")
                return

            confirm = (
                input(f"{Fore.YELLOW}Reset offset for job '{job_name}'? (y/N): ").strip().lower()
            )
            if confirm == "y":
                initial_offset = next(j.initial_offset for j in config.jobs if j.name == job_name)
                if job_name not in state:
                    state[job_name] = {}
                state[job_name]["offset"] = initial_offset
                state[job_name]["status"] = "idle"
                save_state(state_file, state)
                print(
                    f"{Fore.GREEN}✔ Offset for job '{job_name}' reset to {initial_offset} successfully."
                )
            else:
                print("Operation cancelled.")
    except Exception as e:
        print(f"{Fore.RED}Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="telegram-protected-media-forwarder: Resilient Telegram message & media migrations. Created by SadinKai."
    )
    subparsers = parser.add_subparsers(title="Commands", dest="command")

    # Command: start
    subparsers.add_parser("start", help="Starts processing and forwarding configured jobs")

    # Command: setup
    subparsers.add_parser("setup", help="Launch interactive setup wizard")

    # Command: validate
    subparsers.add_parser("validate", help="Validates project configuration files and variables")

    # Command: doctor
    subparsers.add_parser("doctor", help="Check and troubleshoot system health diagnostics report")

    # Command: list-chats
    parser_list = subparsers.add_parser(
        "list-chats", help="Discover and list available Telegram chats"
    )
    parser_list.add_argument(
        "--search", help="Search string to filter chat list by title (case-insensitive)"
    )

    # Command: test-connection
    subparsers.add_parser(
        "test-connection", help="Tests connectivity and credentials with Telegram API"
    )

    # Command: status
    subparsers.add_parser(
        "status", help="Displays current forwarding state offsets and active job status"
    )

    # Command: reset-offset
    parser_reset = subparsers.add_parser(
        "reset-offset", help="Resets forwarding state offset for specified job(s)"
    )
    group = parser_reset.add_mutually_exclusive_group()
    group.add_argument("--job", help="Name of the specific job to reset")
    group.add_argument("--all", action="store_true", help="Reset offsets for all configured jobs")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "start":
        cmd_start(args)
    elif args.command == "setup":
        cmd_setup(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "doctor":
        cmd_doctor(args)
    elif args.command == "list-chats":
        cmd_list_chats(args)
    elif args.command == "test-connection":
        cmd_test_connection(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "reset-offset":
        cmd_reset_offset(args)


if __name__ == "__main__":
    main()
