# Configuration Guide

The **telegram-protected-media-forwarder** supports configuration through environment variables (using a `.env` file) and an INI configuration file (`config.ini`).

The setup wizard handles generating these configurations automatically, meaning you do not need to edit them manually.

---

## 1. Telegram API Credentials Walkthrough (For Beginners)

Before running this tool, you must create a Telegram application to obtain your personal API credentials. These allow you to connect securely to the Telegram servers.

> [!WARNING]
> **CRITICAL SECURITY WARNING**: Your API ID, API Hash, and the session files generated in the `.sessions/` folder (specifically `forwarder.session`) are sensitive access tokens. Anyone who has them can log into and control your Telegram account! **NEVER** share these credentials or files with anyone, and do not upload them to GitHub.

### Step-by-Step API Registration
1. Open your web browser and navigate to **[my.telegram.org](https://my.telegram.org)**.
2. Under **"Your Phone Number"**, enter your phone number in international format (e.g., `+12345678900`) and click **Next**.
3. **Check your Telegram app**: A login code will be sent to you *directly inside the Telegram app* (from the official Telegram account). It will NOT arrive as an SMS.
4. Copy the code from the chat, paste it into the web browser, and click **Sign In**.
5. Click on the **"API development tools"** link.
6. Fill in the form to create a new application:
   * **App title**: Enter any name you like (e.g., `My Media Migrator`).
   * **Short name**: Enter a short alphanumeric word (e.g., `mymediamigrator`).
   * **URL / Description**: You can leave these completely blank.
   * *(Note: The names are arbitrary and are only used to register your account as an API consumer.)*
7. Click **Create application**.
8. Once created, you will see your app's details:
   * **App api_id**: A 7-10 digit number (e.g., `1234567`).
   * **App api_hash**: A 32-character text string (e.g., `abcd1234efgh5678ijkh9012lmno3456`).
9. Keep this page open or copy these values somewhere safe. You will enter them in the setup wizard (`python main.py setup`).

---

## 2. Environment Variables (`.env`)

Secrets and runtime environment parameters are stored in the `.env` file:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `API_ID` | Telegram API ID from [my.telegram.org](https://my.telegram.org) (Required) | `1234567` |
| `API_HASH` | Telegram API Hash from [my.telegram.org](https://my.telegram.org) (Required) | `abcd1234efgh5678ijkh9012lmno3456` |
| `STRING_SESSION` | Pre-authenticated Telethon session string. Useful for headless or cloud deployments. | `1BJWap1wBu8...` |
| `STATE_FILE_PATH` | Path to save the progress offsets registry JSON file. | `data/state.json` |
| `DOWNLOAD_DIR` | Directory where protected media is temporarily downloaded. | `downloads` |

---

## 3. Config File (`config.ini`)

Used for setting global parameters and defining multiple forwarding jobs.

### `[General]` Section
Overrides default options for all forwarding tasks:

```ini
[General]
api_id = YOUR_API_ID
api_hash = YOUR_API_HASH
download_dir = downloads
log_level = INFO
keep_downloads = false
max_retries = 3
upload_delay = 3.0
flood_wait_limit = 300
```

- **`download_dir`**: The folder where media files are saved during transfer.
- **`log_level`**: Controls logging verbosity. Allowed values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.
- **`keep_downloads`**: If set to `true`, downloaded media will not be deleted after being uploaded to the target chat. Defaults to `false`.
- **`max_retries`**: The number of times to retry uploading or sending message content on network failure.
- **`upload_delay`**: Time in seconds to sleep between uploads (prevents spam and rate limits).
- **`flood_wait_limit`**: The maximum duration in seconds the application is allowed to sleep when hit with a `FloodWaitError` before halting the job.

---

## 4. Defining Forward Jobs & Chat Types

Each forward job is represented by a section in `config.ini` with a unique name:

```ini
[ForwardJob1]
from = -1001234567890
to = me
offset = 0
```

- **`from`**: The source chat. Supported formats: Chat IDs (integers, e.g. `-1001234567890`), Usernames (e.g. `@public_channel`), or Saved Messages (`me`). If it is a private chat/channel/group, join it first and select/validate it using the setup wizard or `python main.py list-chats`.
- **`to`**: The destination chat. Supported formats: Chat IDs, Usernames, or Saved Messages (`me`).
- **`offset`**: The initial message ID to start forwarding from. The app will fetch messages with IDs greater than this value. Note that runtime progress offsets are saved in `data/state.json` and will override this once the job has started running.

### What is "Saved Messages" / `me`?
* **Saved Messages** (referenced as `me` in the configuration) is your personal, private cloud storage space inside Telegram.
* Setting `to = me` tells the application to forward all media to your own Saved Messages page.

### Private Groups & Channels
* If you want to forward media from a private group or channel, your Telegram account **must** already be a member/subscriber of it.
* You can find its numerical ID or search for it using the interactive chat picker during `python main.py setup` or by running `python main.py list-chats`.

---

## 5. Finding Chat IDs

Instead of copying numbers manually, run the built-in search tool:
```bash
python main.py list-chats --search "My Channel"
```
This lists matching names, types (Saved Messages, User, Group, Supergroup, or Channel), write access permissions, and numerical IDs.
