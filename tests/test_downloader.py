import os
import shutil
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest

from config.settings import AppConfig
from telegram.downloader import download_message_media


@pytest.fixture
def temp_download_dir():
    # Setup temporary directory for downloads
    dir_path = tempfile.mkdtemp()
    yield dir_path
    # Cleanup directory
    shutil.rmtree(dir_path, ignore_errors=True)


@pytest.mark.asyncio
async def test_download_photo_size_progressive(temp_download_dir):
    """Tests that PhotoSizeProgressive size is correctly parsed and downloader proceeds."""
    # Setup config
    config = MagicMock(spec=AppConfig)
    config.download_dir = temp_download_dir

    # Mock photo size progressive structure
    size_progressive = MagicMock()
    size_progressive.sizes = [1024, 2048, 5000]
    # Remove 'size' attribute if it exists in mock
    if hasattr(size_progressive, "size"):
        delattr(size_progressive, "size")
    if hasattr(size_progressive, "bytes"):
        delattr(size_progressive, "bytes")

    photo = MagicMock()
    photo.sizes = [size_progressive]

    media = MagicMock()
    media.photo = photo
    # Ensure it behaves like it has photo and not document
    media.document = None

    message = MagicMock()
    message.id = 777
    message.media = media

    # Mock client and create mock download action writing a dummy file
    client = MagicMock()

    async def mock_download(*args, **kwargs):
        # The file is specified via kwarg 'file' or positional
        file_path = kwargs.get("file")
        with open(file_path, "wb") as f:
            f.write(b"a" * 5000)
        return file_path

    client.download_media = AsyncMock(side_effect=mock_download)

    # Execute downloader
    result = await download_message_media(client, message, config)

    assert result != ""
    assert os.path.exists(result)
    assert os.path.getsize(result) == 5000
    assert "photo_777.jpg" in result


@pytest.mark.asyncio
async def test_download_photo_size_standard(temp_download_dir):
    """Tests standard PhotoSize with .size attribute."""
    config = MagicMock(spec=AppConfig)
    config.download_dir = temp_download_dir

    standard_size = MagicMock()
    standard_size.size = 3500
    if hasattr(standard_size, "sizes"):
        delattr(standard_size, "sizes")
    if hasattr(standard_size, "bytes"):
        delattr(standard_size, "bytes")

    photo = MagicMock()
    photo.sizes = [standard_size]

    media = MagicMock()
    media.photo = photo
    media.document = None

    message = MagicMock()
    message.id = 888
    message.media = media

    client = MagicMock()

    async def mock_download(*args, **kwargs):
        file_path = kwargs.get("file")
        with open(file_path, "wb") as f:
            f.write(b"b" * 3500)
        return file_path

    client.download_media = AsyncMock(side_effect=mock_download)

    result = await download_message_media(client, message, config)

    assert result != ""
    assert os.path.exists(result)
    assert os.path.getsize(result) == 3500


@pytest.mark.asyncio
async def test_download_photo_cached_size(temp_download_dir):
    """Tests PhotoCachedSize with .bytes length mapping."""
    config = MagicMock(spec=AppConfig)
    config.download_dir = temp_download_dir

    cached_size = MagicMock()
    cached_size.bytes = b"dummy_bytes_here_123"
    if hasattr(cached_size, "size"):
        delattr(cached_size, "size")
    if hasattr(cached_size, "sizes"):
        delattr(cached_size, "sizes")

    photo = MagicMock()
    photo.sizes = [cached_size]

    media = MagicMock()
    media.photo = photo
    media.document = None

    message = MagicMock()
    message.id = 999
    message.media = media

    client = MagicMock()

    async def mock_download(*args, **kwargs):
        file_path = kwargs.get("file")
        with open(file_path, "wb") as f:
            f.write(cached_size.bytes)
        return file_path

    client.download_media = AsyncMock(side_effect=mock_download)

    result = await download_message_media(client, message, config)

    assert result != ""
    assert os.path.exists(result)
    assert os.path.getsize(result) == len(cached_size.bytes)


@pytest.mark.asyncio
async def test_download_metadata_error_resilience(temp_download_dir):
    """Tests that downloader does not crash when metadata properties trigger exceptions."""
    config = MagicMock(spec=AppConfig)
    config.download_dir = temp_download_dir

    class MalformedMedia:
        @property
        def document(self):
            raise ValueError("Simulated metadata error")

        @property
        def photo(self):
            raise ValueError("Simulated metadata error")

    message = MagicMock()
    message.id = 1212
    message.media = MalformedMedia()

    client = MagicMock()

    async def mock_download(*args, **kwargs):
        file_path = kwargs.get("file")
        with open(file_path, "wb") as f:
            f.write(b"fallback_data")
        return file_path

    client.download_media = AsyncMock(side_effect=mock_download)

    # Downloader should log warning and continue using fallback
    result = await download_message_media(client, message, config)

    assert result != ""
    assert os.path.exists(result)
    assert "media_1212.bin" in result
    assert os.path.getsize(result) > 0
