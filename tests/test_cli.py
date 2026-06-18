import os
import shutil
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

from telethon.tl.types import Channel, Chat, User

from config.settings import AppConfig, ForwardJob
from main import perform_health_check
from setup_wizard import backup_configs
from utils.helpers import get_chat_access, get_chat_type


def test_get_chat_type():
    # 1. User is_self=True -> Saved Messages
    user_self = MagicMock(spec=User)
    user_self.is_self = True
    assert get_chat_type(user_self) == "Saved Messages"

    # 2. User is_self=False -> User
    user_other = MagicMock(spec=User)
    user_other.is_self = False
    assert get_chat_type(user_other) == "User"

    # 3. Chat -> Group
    group_chat = MagicMock(spec=Chat)
    assert get_chat_type(group_chat) == "Group"

    # 4. Channel megagroup=True -> Supergroup
    supergroup = MagicMock(spec=Channel)
    supergroup.megagroup = True
    assert get_chat_type(supergroup) == "Supergroup"

    # 5. Channel megagroup=False -> Channel
    channel = MagicMock(spec=Channel)
    channel.megagroup = False
    assert get_chat_type(channel) == "Channel"


def test_get_chat_access():
    # 1. User -> Read/Write
    user = MagicMock(spec=User)
    assert get_chat_access(user) == "Read/Write"

    # 2. Chat (Group) left=True -> Read Only
    group_left = MagicMock(spec=Chat)
    group_left.left = True
    assert get_chat_access(group_left) == "Read Only"

    # 3. Chat (Group) left=False -> Read/Write
    group_ok = MagicMock(spec=Chat)
    group_ok.left = False
    group_ok.banned_rights = None
    assert get_chat_access(group_ok) == "Read/Write"

    # 4. Channel (Supergroup) left=True -> Read Only
    sg_left = MagicMock(spec=Channel)
    sg_left.megagroup = True
    sg_left.left = True
    assert get_chat_access(sg_left) == "Read Only"

    # 5. Channel (Supergroup) banned from sending -> Read Only
    sg_banned = MagicMock(spec=Channel)
    sg_banned.megagroup = True
    sg_banned.left = False
    sg_banned.banned_rights = MagicMock()
    sg_banned.banned_rights.send_messages = True
    assert get_chat_access(sg_banned) == "Read Only"

    # 6. Channel (Broadcast) creator=True -> Read/Write
    chan_creator = MagicMock(spec=Channel)
    chan_creator.megagroup = False
    chan_creator.left = False
    chan_creator.creator = True
    assert get_chat_access(chan_creator) == "Read/Write"

    # 7. Channel (Broadcast) admin with post_messages -> Read/Write
    chan_admin = MagicMock(spec=Channel)
    chan_admin.megagroup = False
    chan_admin.left = False
    chan_admin.creator = False
    chan_admin.admin_rights = MagicMock()
    chan_admin.admin_rights.post_messages = True
    assert get_chat_access(chan_admin) == "Read/Write"

    # 8. Channel (Broadcast) reader only -> Read Only
    chan_reader = MagicMock(spec=Channel)
    chan_reader.megagroup = False
    chan_reader.left = False
    chan_reader.creator = False
    chan_reader.admin_rights = None
    assert get_chat_access(chan_reader) == "Read Only"


def test_backup_configs():
    # Setup temp working dir to test backups
    temp_dir = tempfile.mkdtemp()
    orig_cwd = os.getcwd()
    os.chdir(temp_dir)

    try:
        # Create dummy config.ini and state.json
        with open("config.ini", "w") as f:
            f.write("dummy_config")
        os.makedirs("data", exist_ok=True)
        with open("data/state.json", "w") as f:
            f.write("dummy_state")

        # Run backup
        backup_configs()

        # Verify backups were created in backups/
        backup_dir = "backups"
        assert os.path.exists(backup_dir)
        files = os.listdir(backup_dir)
        assert any(f.startswith("config_") and f.endswith(".ini") for f in files)
        assert any(f.startswith("state_") and f.endswith(".json") for f in files)
    finally:
        os.chdir(orig_cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_perform_health_check_success():
    """Tests perform_health_check when everything is healthy."""
    temp_dir = tempfile.mkdtemp()
    try:
        config = MagicMock(spec=AppConfig)
        config.api_id = "123456"
        config.api_hash = "abcdef0123456789abcdef0123456789"
        config.state_file_path = os.path.join(temp_dir, "state.json")
        config.download_dir = os.path.join(temp_dir, "downloads")

        job = ForwardJob("TestJob", "@src", "@dst", 0)
        config.jobs = [job]

        # Write dummy state.json
        with open(config.state_file_path, "w") as f:
            f.write("{}")

        # Mock client connection and calls
        client = MagicMock()
        client.get_entity = AsyncMock(return_value="resolved_entity")
        client.send_message = AsyncMock(return_value="sent_message")
        client.delete_messages = AsyncMock()

        with patch("main.create_telegram_client", AsyncMock(return_value=client)):
            success = perform_health_check(config, is_doctor_cmd=True)
            assert success is True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_perform_health_check_failure():
    """Tests perform_health_check when destination chat is write-restricted."""
    temp_dir = tempfile.mkdtemp()
    try:
        config = MagicMock(spec=AppConfig)
        config.api_id = "123456"
        config.api_hash = "abcdef0123456789abcdef0123456789"
        config.state_file_path = os.path.join(temp_dir, "state.json")
        config.download_dir = os.path.join(temp_dir, "downloads")

        job = ForwardJob("TestJob", "@src", "@dst", 0)
        config.jobs = [job]

        # Write dummy state.json
        with open(config.state_file_path, "w") as f:
            f.write("{}")

        # Mock client connection, where send_message fails due to permission restriction
        client = MagicMock()
        client.get_entity = AsyncMock(return_value="resolved_entity")
        client.send_message = AsyncMock(side_effect=Exception("Write Forbidden"))

        with patch("main.create_telegram_client", AsyncMock(return_value=client)):
            success = perform_health_check(config, is_doctor_cmd=True)
            assert success is False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
