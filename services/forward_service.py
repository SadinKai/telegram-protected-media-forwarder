import asyncio
import json
import logging
import os
from datetime import datetime

from telethon import TelegramClient
from telethon.errors.rpcerrorlist import ChatForwardsRestrictedError, FloodWaitError
from telethon.tl.patched import MessageService

from config.settings import AppConfig
from telegram.downloader import download_message_media
from telegram.uploader import send_text_message, upload_file
from utils.helpers import intify

logger = logging.getLogger("forwarder")


def load_state(state_file_path: str) -> dict:
    """Loads the forwarding state from the JSON state file."""
    if not os.path.exists(state_file_path):
        return {}
    try:
        with open(state_file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read state file ({e}). Starting with empty state.")
        return {}


def save_state(state_file_path: str, state: dict):
    """Saves the forwarding state atomically to the JSON state file."""
    temp_path = f"{state_file_path}.tmp"
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(state_file_path), exist_ok=True)
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
        # Atomic rename
        os.replace(temp_path, state_file_path)
    except Exception as e:
        logger.error(f"Failed to save state file atomically: {e}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def update_job_state(state_file_path: str, job_name: str, offset: int, status: str = "running"):
    """Updates the state offset for a specific job and saves it."""
    state = load_state(state_file_path)
    state[job_name] = {"offset": offset, "last_run": datetime.now().isoformat(), "status": status}
    save_state(state_file_path, state)


async def run_forward_jobs(client: TelegramClient, config: AppConfig):
    """
    Main entry point for running all configured forward jobs.
    Runs each job sequentially, tracking offsets and handling errors.
    """
    state_file = config.state_file_path
    state = load_state(state_file)

    logger.info(f"Starting forwarding process for {len(config.jobs)} jobs...")

    for job in config.jobs:
        logger.info(f"--- Starting Job: '{job.name}' ---")

        # Determine starting offset
        job_state = state.get(job.name, {})
        offset = job_state.get("offset", job.initial_offset)
        logger.info(f"Starting offset for job '{job.name}': {offset}")

        try:
            # Resolve source and destination entities
            from_entity = await client.get_entity(intify(job.from_chat))
            to_entity = await client.get_entity(intify(job.to_chat))
        except Exception as e:
            logger.error(
                f"Failed to resolve chat entities for job '{job.name}': {e}. Skipping job."
            )
            update_job_state(state_file, job.name, offset, status="failed")
            continue

        error_occurred = False
        message_count = 0

        try:
            # Iterate through messages in reverse order (oldest to newest) starting from offset
            async for message in client.iter_messages(from_entity, reverse=True, offset_id=offset):
                # Skip service messages (e.g. chat creation, pinned message notifications)
                if isinstance(message, MessageService):
                    continue

                logger.info(f"Processing message ID: {message.id}")
                success = False

                # 1. Attempt Standard Telegram Forwarding
                try:
                    # telethon client.forward_messages forwards messages directly
                    await client.forward_messages(to_entity, message)
                    logger.info(
                        f"Successfully forwarded message {message.id} via standard Telegram forwarding."
                    )
                    success = True
                except ChatForwardsRestrictedError:
                    # 2. Fallback to Protected Media Mode (Download & Re-upload)
                    logger.warning(
                        f"Message {message.id} is protected/restricted from forwarding. "
                        "Falling back to Protected Media Mode (Download & Re-upload)..."
                    )

                    if message.media:
                        # Download media locally
                        local_path = await download_message_media(client, message, config)
                        if local_path and os.path.exists(local_path):
                            # Upload to destination
                            success = await upload_file(
                                client=client,
                                entity=to_entity,
                                file_path=local_path,
                                caption=message.text or "",
                                config=config,
                            )

                            # Cleanup file if configured
                            if not config.keep_downloads:
                                try:
                                    os.remove(local_path)
                                    logger.info(f"Removed temporary local file: {local_path}")
                                except Exception as cleanup_err:
                                    logger.warning(
                                        f"Could not delete temporary file {local_path}: {cleanup_err}"
                                    )
                        else:
                            logger.error(
                                f"Protected media download failed for message {message.id}."
                            )
                    else:
                        # Plain text message that was restricted (e.g., text post in a protected channel)
                        success = await send_text_message(
                            client, to_entity, message.text or "", config
                        )

                except FloodWaitError as fwe:
                    if fwe.seconds > config.flood_wait_limit:
                        logger.error(
                            f"Flood wait limit exceeded ({fwe.seconds}s > {config.flood_wait_limit}s). Aborting job."
                        )
                        raise fwe
                    logger.warning(f"Flood wait: Sleeping for {fwe.seconds} seconds...")
                    await asyncio.sleep(fwe.seconds)
                    # Don't increment/update offset yet, we will retry this message on the next tick
                    continue
                except Exception as e:
                    logger.exception(f"Failed to forward message {message.id}: {e}")
                    error_occurred = True
                    break

                if success:
                    # Update offset and persist state immediately
                    offset = message.id
                    update_job_state(state_file, job.name, offset, status="running")
                    message_count += 1

                    # Upload delay configuration between operations
                    if config.upload_delay > 0:
                        await asyncio.sleep(config.upload_delay)
                else:
                    logger.error(
                        f"Failed to process message {message.id}. Halting job execution to prevent gaps."
                    )
                    error_occurred = True
                    break

        except FloodWaitError as fwe:
            logger.error(f"Job '{job.name}' aborted due to FloodWaitError: {fwe}")
            error_occurred = True
        except Exception as e:
            logger.exception(f"Unexpected error while processing job '{job.name}': {e}")
            error_occurred = True

        status = "failed" if error_occurred else "completed"
        update_job_state(state_file, job.name, offset, status=status)
        logger.info(
            f"Finished Job: '{job.name}'. Status: {status}. Processed {message_count} messages."
        )

    logger.info("All forwarding jobs completed.")
