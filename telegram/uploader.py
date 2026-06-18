import asyncio
import logging
import os

from telethon import TelegramClient
from telethon.errors.rpcerrorlist import FloodWaitError
from tqdm import tqdm

from config.settings import AppConfig

logger = logging.getLogger("forwarder")


class UploadProgressBar:
    """Helper class to report upload progress via tqdm."""

    def __init__(self, filename: str, total_bytes: int):
        self.pbar = tqdm(
            total=total_bytes or 0,
            unit="B",
            unit_scale=True,
            desc=f"Uploading {filename[:25]}",
            leave=False,
        )

    def callback(self, current, total):
        self.pbar.update(current - self.pbar.n)

    def close(self):
        self.pbar.close()


async def upload_file(
    client: TelegramClient, entity: any, file_path: str, caption: str, config: AppConfig
) -> bool:
    """
    Uploads a file to a destination entity (chat/channel/user).
    Includes a progress bar, handles FloodWaitError and connection retries.
    """
    if not os.path.exists(file_path):
        logger.error(f"Cannot upload file: {file_path} does not exist.")
        return False

    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    retries = 0
    while retries <= config.max_retries:
        progress = UploadProgressBar(filename, file_size)
        try:
            # send_file uploads the file and sends it to the target entity
            await client.send_file(
                entity, file_path, caption=caption or "", progress_callback=progress.callback
            )
            progress.close()
            logger.info(f"Successfully uploaded: {filename}")
            return True

        except FloodWaitError as fwe:
            progress.close()
            if fwe.seconds > config.flood_wait_limit:
                logger.error(
                    f"FloodWaitError: Required wait of {fwe.seconds}s exceeds limit ({config.flood_wait_limit}s). Aborting upload."
                )
                raise fwe
            logger.warning(f"FloodWaitError: Waiting for {fwe.seconds} seconds before retrying...")
            await asyncio.sleep(fwe.seconds)
            # Do not increment retries for FloodWait
            continue

        except (ConnectionError, asyncio.TimeoutError) as ce:
            progress.close()
            retries += 1
            logger.warning(
                f"Connection issue encountered ({ce}). Retry {retries}/{config.max_retries}..."
            )
            if retries > config.max_retries:
                logger.error("Max retries exceeded for file upload. Aborting.")
                return False
            await asyncio.sleep(2**retries)  # Exponential backoff

        except Exception as e:
            progress.close()
            logger.exception(f"Unexpected error while uploading {filename}: {e}")
            return False

    return False


async def send_text_message(
    client: TelegramClient, entity: any, text: str, config: AppConfig
) -> bool:
    """
    Sends a plain text message to the target entity.
    Includes retry logic and FloodWait handling.
    """
    retries = 0
    while retries <= config.max_retries:
        try:
            await client.send_message(entity, text)
            logger.info("Successfully sent text message.")
            return True

        except FloodWaitError as fwe:
            if fwe.seconds > config.flood_wait_limit:
                logger.error(
                    f"FloodWaitError: Required wait of {fwe.seconds}s exceeds limit ({config.flood_wait_limit}s). Aborting."
                )
                raise fwe
            logger.warning(f"FloodWaitError: Waiting for {fwe.seconds} seconds before retrying...")
            await asyncio.sleep(fwe.seconds)
            continue

        except (ConnectionError, asyncio.TimeoutError) as ce:
            retries += 1
            logger.warning(
                f"Connection issue encountered ({ce}). Retry {retries}/{config.max_retries}..."
            )
            if retries > config.max_retries:
                logger.error("Max retries exceeded for text message send. Aborting.")
                return False
            await asyncio.sleep(2**retries)

        except Exception as e:
            logger.exception(f"Unexpected error while sending text message: {e}")
            return False

    return False
