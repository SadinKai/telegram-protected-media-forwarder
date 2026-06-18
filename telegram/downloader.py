import logging
import os

from telethon import TelegramClient
from telethon.tl.types import Message
from tqdm import tqdm

from config.settings import AppConfig
from utils.helpers import is_safe_path, sanitize_filename

logger = logging.getLogger("forwarder")


class TqdmProgress:
    """Helper class to report download/upload progress via tqdm."""

    def __init__(self, filename: str, total: int):
        self.total = total or 0
        self.pbar = tqdm(
            total=self.total,
            unit="B",
            unit_scale=True,
            desc=f"Downloading {filename[:25]}",
            leave=False,
        )

    def callback(self, current, total):
        # Dynamically set total if it was initialized to 0 but is received from Telegram in the callback
        if (self.total is None or self.total == 0) and total:
            self.total = total
            self.pbar.total = total
        self.pbar.update(current - self.pbar.n)

    def close(self):
        self.pbar.close()


async def download_message_media(
    client: TelegramClient, message: Message, config: AppConfig
) -> str:
    """
    Downloads media from a Telegram message.
    Ensures the downloader never crashes due to media metadata structure anomalies.
    Returns the absolute path to the downloaded file, or empty string if failed.
    """
    if not message.media:
        return ""

    raw_filename = ""
    file_size = 0
    is_photo = False

    # 1. Resilient Metadata Parsing
    try:
        if hasattr(message.media, "document") and message.media.document:
            doc = message.media.document
            file_size = getattr(doc, "size", 0) or 0

            # Extract filename from document attributes
            doc_attributes = getattr(doc, "attributes", []) or []
            for attr in doc_attributes:
                if hasattr(attr, "file_name") and attr.file_name:
                    raw_filename = attr.file_name
                    break

            if not raw_filename:
                # Fallback extension detection
                mime = getattr(doc, "mime_type", "") or ""
                ext = "." + mime.split("/")[-1] if "/" in mime else ".bin"
                raw_filename = f"document_{message.id}{ext}"

        elif hasattr(message.media, "photo") and message.media.photo:
            is_photo = True
            photo = message.media.photo
            photo_sizes = getattr(photo, "sizes", []) or []

            if photo_sizes:
                # Retrieve the largest size variant safely
                largest_size_obj = photo_sizes[-1]

                # Check different Telethon photo size object representations:
                # - PhotoSize: has .size
                if hasattr(largest_size_obj, "size"):
                    file_size = largest_size_obj.size or 0
                # - PhotoSizeProgressive: has .sizes (list of intermediate sizes)
                elif hasattr(largest_size_obj, "sizes") and isinstance(
                    largest_size_obj.sizes, list
                ):
                    file_size = largest_size_obj.sizes[-1] if largest_size_obj.sizes else 0
                # - PhotoCachedSize / PhotoStrippedSize: has .bytes containing size
                elif hasattr(largest_size_obj, "bytes") and largest_size_obj.bytes:
                    file_size = len(largest_size_obj.bytes)

            raw_filename = f"photo_{message.id}.jpg"
        else:
            raw_filename = f"media_{message.id}.bin"

    except Exception as metadata_err:
        logger.warning(
            f"Failed to parse media metadata for message {message.id}: {metadata_err}. "
            "Using generic fallbacks to proceed with download."
        )
        is_photo = False
        file_size = 0
        raw_filename = f"media_{message.id}.bin"

    # Ensure clean values
    if file_size is None or not isinstance(file_size, int) or file_size < 0:
        file_size = 0
    if not raw_filename:
        raw_filename = f"media_{message.id}.bin"

    # 2. Sanitize and Form Output Path
    safe_name = f"msg_{message.id}_{sanitize_filename(raw_filename)}"
    download_dir = os.path.abspath(config.download_dir)
    dest_path = os.path.join(download_dir, safe_name)

    # Path traversal protection
    if not is_safe_path(download_dir, dest_path):
        logger.error(f"Media download path is unsafe (path traversal detected): {dest_path}")
        return ""

    # 3. Duplicate Detection
    if os.path.exists(dest_path):
        local_size = os.path.getsize(dest_path)
        if is_photo:
            if local_size > 0:
                logger.info(
                    f"Duplicate photo detected: {safe_name} already exists. Skipping download."
                )
                return dest_path
        else:
            if local_size == file_size and file_size > 0:
                logger.info(
                    f"Duplicate document detected: {safe_name} already exists with matching size. Skipping download."
                )
                return dest_path

    logger.info(f"Downloading media for message {message.id} ({safe_name})...")
    progress = TqdmProgress(safe_name, file_size)

    try:
        # Perform download
        result_path = await client.download_media(
            message, file=dest_path, progress_callback=progress.callback
        )
        progress.close()

        # 4. Post-Download Validation
        if result_path and os.path.exists(result_path):
            downloaded_size = os.path.getsize(result_path)

            if downloaded_size <= 0:
                logger.error(
                    f"Download validation failed: Resulting file size is 0 bytes for message {message.id}."
                )
                return ""

            if not is_photo:
                # Size verification only for documents if expected size is known
                if file_size > 0 and downloaded_size != file_size:
                    logger.error(
                        f"Download size mismatch for document {message.id}. Expected {file_size}, got {downloaded_size}"
                    )
                    return ""

            logger.info(
                f"Successfully downloaded and validated media: {result_path} ({downloaded_size} bytes)"
            )
            return os.path.abspath(result_path)
        else:
            logger.error(f"Failed to download media for message {message.id}: No path returned.")
            return ""

    except Exception as e:
        progress.close()
        logger.exception(f"Error occurred while downloading media for message {message.id}: {e}")
        return ""
