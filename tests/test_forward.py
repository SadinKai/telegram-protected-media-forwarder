import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telethon.errors.rpcerrorlist import ChatForwardsRestrictedError

from config.settings import AppConfig, ForwardJob
from services.forward_service import load_state, run_forward_jobs


@pytest.mark.asyncio
async def test_run_forward_jobs_standard_flow(monkeypatch):
    """Tests the happy path where standard forwarding succeeds."""
    # Create temporary state path
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_state:
        state_path = temp_state.name

    try:
        # Mock configuration
        config = MagicMock(spec=AppConfig)
        config.state_file_path = state_path
        config.keep_downloads = False
        config.upload_delay = 0
        config.max_retries = 1

        job = ForwardJob("TestJob", "@src", "@dst", 0)
        config.jobs = [job]

        # Mock Telegram Client
        client = MagicMock()
        client.get_entity = AsyncMock(return_value="resolved_entity")

        # Mock message list
        mock_msg = MagicMock()
        mock_msg.id = 42
        mock_msg.media = None
        mock_msg.text = "Hello World"

        # Async generator for iter_messages
        async def mock_iter_messages(*args, **kwargs):
            yield mock_msg

        client.iter_messages = mock_iter_messages
        client.forward_messages = AsyncMock()

        # Run forward service
        await run_forward_jobs(client, config)

        # Check standard forwarding was called
        client.forward_messages.assert_called_once_with("resolved_entity", mock_msg)

        # Verify state file was updated
        updated_state = load_state(state_path)
        assert "TestJob" in updated_state
        assert updated_state["TestJob"]["offset"] == 42
        assert updated_state["TestJob"]["status"] == "completed"

    finally:
        if os.path.exists(state_path):
            os.remove(state_path)


@pytest.mark.asyncio
async def test_run_forward_jobs_protected_media_fallback(monkeypatch):
    """Tests the fallback flow when standard forwarding raises ChatForwardsRestrictedError."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_state:
        state_path = temp_state.name

    # Create a dummy media file that exists on disk
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_media:
        temp_media_path = temp_media.name
        temp_media.write(b"dummy_data")

    try:
        # Mock configuration
        config = MagicMock(spec=AppConfig)
        config.state_file_path = state_path
        config.keep_downloads = False
        config.upload_delay = 0
        config.max_retries = 1

        job = ForwardJob("ProtectedJob", "@src", "@dst", 0)
        config.jobs = [job]

        # Mock Telegram Client
        client = MagicMock()
        client.get_entity = AsyncMock(return_value="resolved_entity")

        # Message with protected media
        mock_msg = MagicMock()
        mock_msg.id = 101
        mock_msg.media = MagicMock()
        mock_msg.text = "Protected Caption"

        async def mock_iter_messages(*args, **kwargs):
            yield mock_msg

        client.iter_messages = mock_iter_messages

        # Force forward_messages to raise ChatForwardsRestrictedError
        client.forward_messages = AsyncMock(side_effect=ChatForwardsRestrictedError(request=None))

        # Patch the downloader and uploader modules
        with patch(
            "services.forward_service.download_message_media",
            AsyncMock(return_value=temp_media_path),
        ) as mock_download, patch(
            "services.forward_service.upload_file", AsyncMock(return_value=True)
        ) as mock_upload, patch(
            "os.remove"
        ) as mock_remove:

            # Run forward service
            await run_forward_jobs(client, config)

            # Verify download and upload fallback were triggered
            mock_download.assert_called_once_with(client, mock_msg, config)
            mock_upload.assert_called_once_with(
                client=client,
                entity="resolved_entity",
                file_path=temp_media_path,
                caption="Protected Caption",
                config=config,
            )
            mock_remove.assert_called_once_with(temp_media_path)

        # Verify state file was updated
        updated_state = load_state(state_path)
        assert "ProtectedJob" in updated_state
        assert updated_state["ProtectedJob"]["offset"] == 101
        assert updated_state["ProtectedJob"]["status"] == "completed"

    finally:
        if os.path.exists(state_path):
            os.remove(state_path)
        if os.path.exists(temp_media_path):
            try:
                os.remove(temp_media_path)
            except Exception:
                pass


@pytest.mark.asyncio
async def test_run_forward_jobs_protected_photo_fallback(monkeypatch):
    """Tests the fallback flow specifically for a protected photo media type."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_state:
        state_path = temp_state.name

    # Create a dummy photo file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_photo:
        temp_photo_path = temp_photo.name
        temp_photo.write(b"dummy_photo_data")

    try:
        # Mock configuration
        config = MagicMock(spec=AppConfig)
        config.state_file_path = state_path
        config.keep_downloads = False
        config.upload_delay = 0
        config.max_retries = 1

        job = ForwardJob("PhotoJob", "@src", "@dst", 0)
        config.jobs = [job]

        # Mock Telegram Client
        client = MagicMock()
        client.get_entity = AsyncMock(return_value="resolved_entity")

        # Message with photo media representation
        mock_photo = MagicMock()
        mock_photo.sizes = [MagicMock()]

        mock_msg = MagicMock()
        mock_msg.id = 202
        mock_msg.media = MagicMock()
        mock_msg.media.photo = mock_photo
        mock_msg.media.document = None
        mock_msg.text = "Photo Caption"

        async def mock_iter_messages(*args, **kwargs):
            yield mock_msg

        client.iter_messages = mock_iter_messages
        client.forward_messages = AsyncMock(side_effect=ChatForwardsRestrictedError(request=None))

        # Patch the downloader and uploader modules
        with patch(
            "services.forward_service.download_message_media",
            AsyncMock(return_value=temp_photo_path),
        ) as mock_download, patch(
            "services.forward_service.upload_file", AsyncMock(return_value=True)
        ) as mock_upload, patch(
            "os.remove"
        ) as mock_remove:

            # Run forward service
            await run_forward_jobs(client, config)

            # Verify download and upload fallback were triggered
            mock_download.assert_called_once_with(client, mock_msg, config)
            mock_upload.assert_called_once_with(
                client=client,
                entity="resolved_entity",
                file_path=temp_photo_path,
                caption="Photo Caption",
                config=config,
            )
            mock_remove.assert_called_once_with(temp_photo_path)

        # Verify state file was updated
        updated_state = load_state(state_path)
        assert "PhotoJob" in updated_state
        assert updated_state["PhotoJob"]["offset"] == 202
        assert updated_state["PhotoJob"]["status"] == "completed"

    finally:
        if os.path.exists(state_path):
            os.remove(state_path)
        if os.path.exists(temp_photo_path):
            try:
                os.remove(temp_photo_path)
            except Exception:
                pass
