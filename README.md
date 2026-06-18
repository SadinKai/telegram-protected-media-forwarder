# telegram-protected-media-forwarder

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.8%2B-green.svg)](https://python.org)
[![Build Status](https://img.shields.io/badge/Build-passing-brightgreen.svg)](#)

A production-grade Telegram media migration and forwarding tool. It downloads media from Telegram chats, bots, or channels—**including protected chats where media copying or forwarding is restricted**—and uploads them to destination chats while maintaining robust progress tracking, fault tolerance, and resume capabilities.

The entire experience is built to be beginner-friendly. You do not need to look up numerical Chat IDs, run complex commands, or manually edit configuration files. The setup wizard and diagnostics handle it all.

---

## Key Features

- **🛡️ Protected Media Mode**: Automatically bypasses Telegram's forwarding restrictions (`ChatForwardsRestrictedError`) by downloading files locally and uploading them as fresh files with original captions.
- **✨ Interactive Chat Picker**: Search and select source and destination chats by name directly inside the setup wizard—no copying IDs required.
- **🩺 Self-Healing Diagnostics (`doctor`)**: Central system health check that verifies credentials, file permissions, connections, and access rights, providing clear recovery actions.
- **🔄 State Persistence**: Progress is saved atomically to `data/state.json` after every single message, allowing instant resume after a crash or shutdown.
- **⚙️ Configurable CLI & Setup Wizard**: Choose between Quick Setup (Recommended) and Advanced Setup. Generates `.env` and `config.ini` files with safe backups.
- **📁 Duplicate & Name Protection**: Handles safe filenames to prevent path traversals and automatically skips downloading duplicate media when resuming jobs.
- **🚦 Flood & Timeout Handling**: Automatically pauses execution when hit with a `FloodWaitError` and implements exponential backoffs for network drops.
- **🐳 Docker Ready**: Full container configurations (`Dockerfile`, `docker-compose.yml`) supporting persistent data and session mounts.

> [!WARNING]
> **CRITICAL SECURITY WARNING**: The `.sessions/` folder (specifically `.sessions/forwarder.session`) contains your Telegram login session keys. Anyone who gains access to these files can fully control your Telegram account! **NEVER** share your session files, API ID, or API Hash with anyone, or commit them to public repositories.

---

## Project Structure

```
telegram-protected-media-forwarder/
├── config/                 # Settings loading and environment validations
├── telegram/               # Telegram client initialization, downloaders, and uploaders
├── services/               # Orchestration service for handling forward jobs and fallback
├── utils/                  # Helper utilities for path checking, math, and logging
├── tests/                  # Automated pytest suite covering mock and unit checks
├── docs/                   # Exhaustive project installation and troubleshooting guides
├── data/                   # Registry directories for persistent progress tracking state
├── downloads/              # Temporary local disk cache for protected media files
├── logs/                   # System runtime logs with automated file rotation
├── README.md               # Main project introduction and quick start guide
├── LICENSE                 # MIT license details and attribution
├── main.py                 # Core CLI entry point for executing jobs/diagnostics
├── setup_wizard.py         # Interactive setup wizard for onboarding configuration
└── pyproject.toml          # Project metadata, dependencies, and packaging specs
```

---

## Quick Start (Beginner Friendly)

### 1. Installation

You can download and set up the project in two ways:

#### Option A: Download ZIP (No Git needed)
1. Go to the top of this GitHub repository page.
2. Click the green **Code** button and select **Download ZIP**.
3. Extract the downloaded `.zip` file on your computer.
4. Open your command prompt/terminal (CMD or PowerShell on Windows) and navigate to the extracted folder:
   ```cmd
   # Enter the exact extracted folder name (usually depends on the branch name):
   cd path/to/telegram-protected-media-forwarder-main
   # or
   cd path/to/telegram-protected-media-forwarder-master
   ```

#### Option B: Clone via Git
```bash
git clone https://github.com/<OWNER>/telegram-protected-media-forwarder.git
cd telegram-protected-media-forwarder
```

#### Set Up Python and Dependencies
```bash
# Create a virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (Command Prompt):
venv\Scripts\activate.bat
# On Windows (PowerShell):
# If script execution is disabled, run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
venv\Scripts\Activate.ps1
# On Linux / macOS:
source venv/bin/activate

# Install dependencies (cryptg speedups are optional and omitted for easier Windows installs)
pip install -r requirements.txt
```
> [!TIP]
> **Windows Users**: For detailed step-by-step assistance installing Python, checking the "Add Python to PATH" box, and troubleshooting activation issues, read the [Installation Guide](docs/INSTALL.md).

### 2. Run Setup Wizard

Launch the interactive setup wizard, which will connect to Telegram and guide you through configuration step-by-step:
```bash
python main.py setup
```
- Select **Quick Setup** (Recommended) or **Advanced Setup**.
- Connect to Telegram interactively by entering your verification code.
- Search and select your source and destination chats by name!

### 3. Verify Configuration Health

Ensure everything is configured and authenticated correctly:
```bash
python main.py doctor
```
This runs a diagnostics checklist verifying connections, write access, and session integrity.

### 4. Start Forwarding

Start migrating your media:
```bash
python main.py start
```

---

## Onboarding Commands & Chat Discovery

### Chat Discovery (`list-chats`)

List all dialogs accessible by your account sorted alphabetically:
```bash
python main.py list-chats
```
Outputs a clean table containing:
- **NAME**: The name of the chat or group.
- **TYPE**: Saved Messages, User, Group, Supergroup, or Channel.
- **ACCESS**: Access level (Read/Write or Read Only).
- **ID**: The numerical Chat ID.

### Chat Search

Search for a specific chat by name (case-insensitive, partial matching):
```bash
python main.py list-chats --search "movie"
```

### Self-Healing Diagnostics (`doctor`)

Check all parts of the application:
```bash
python main.py doctor
```
If anything is wrong, the tool prints clear explanations:
- What failed
- Why it failed
- Exact instructions on how to fix it

---

## CLI Command Reference

- **`python main.py start`**: Start forwarding messages sequentially.
- **`python main.py setup`**: Launch the interactive setup wizard.
- **`python main.py validate`**: Run the system validation report checklist.
- **`python main.py doctor`**: Perform system diagnostics and display recovery steps.
- **`python main.py list-chats [--search <term>]`**: Discover available chats and print metadata.
- **`python main.py test-connection`**: Run a simple credentials connectivity test.
- **`python main.py status`**: Display current offsets, active jobs, and status.
- **`python main.py reset-offset [--job <job_name> | --all]`**: Reset offsets in the progress registry.

---

## Development & Testing

Ensure you install development dependencies:
```bash
pip install -e .[dev]
pytest tests/
```

---

## Author

Telegram Protected Media Forwarder

Created and maintained by SadinKai.
