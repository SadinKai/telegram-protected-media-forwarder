# Installation Guide

This guide provides step-by-step, beginner-friendly instructions to install, configure, and verify the **telegram-protected-media-forwarder** across different platforms.

---

## 1. Prerequisites (For Beginners)

### Step A: Install Python on Windows
If you already have Python installed, make sure it is version **3.8** or higher. If you don't have it:
1. Go to the official [Python Downloads page](https://www.python.org/downloads/).
2. Click the yellow button to download Python for Windows.
3. Open the downloaded installer file.
4. **CRITICAL STEP**: At the bottom of the installer window, check the box that says **"Add python.exe to PATH"** (or **"Add Python to environment variables"**). If you miss this, your computer will not understand the `python` command!
5. Click **Install Now** and follow the instructions.

### Step B: Download the Code (No Git Required)
If you don't know what GitHub or Git is, do not worry:
1. Go to the main project page on GitHub.
2. Click the green **Code** button near the top right.
3. Select **Download ZIP**.
4. Save the file and extract it (unzip it) to a folder of your choice (e.g., your Desktop or Documents folder).
5. **NOTE ON FOLDER NAMES**: Depending on the default repository branch, the extracted folder will be named:
   * `telegram-protected-media-forwarder-main`
   * or
   * `telegram-protected-media-forwarder-master`
   * Please ensure you look at the folder's name after extracting. You must enter this specific folder before running setup commands.

---

## 2. Local Setup & Commands

Open your terminal:
* **Option 1: Command Prompt (CMD)** - Press `Win + R`, type `cmd`, and press Enter. (Recommended for beginners as it has no execution restrictions).
* **Option 2: PowerShell** - Press `Win + X` and select **Terminal** or **PowerShell**.

### 1. Navigate to the Folder
Use the `cd` (change directory) command to go into the folder where you extracted the files:
```cmd
# For standard ZIP downloads, navigate to the specific extracted folder name:
cd path/to/telegram-protected-media-forwarder-main
# or
cd path/to/telegram-protected-media-forwarder-master
```
*(Tip: In Windows Explorer, you can open the folder you extracted, type `cmd` in the address bar at the top of the window, and press Enter to open Command Prompt directly in that folder!)*

### 2. Set Up a Virtual Environment
A virtual environment keeps the dependencies of this project separate from the rest of your computer.

#### Linux Users (Debian/Ubuntu Note)
On some Linux distributions (such as Ubuntu and Debian), Python's virtual environment package (`venv`) is stripped out of the default Python installation to minimize base system size. You must install it first using:
```bash
sudo apt update && sudo apt install python3-venv
```
Once installed, or if you are on Windows/macOS, you can proceed to create and activate the virtual environment.

Create the virtual environment:
```bash
python -m venv venv
```

Activate the virtual environment:
* **If you are using Command Prompt (CMD)**:
  ```cmd
  venv\Scripts\activate.bat
  ```
* **If you are using PowerShell**:
  ```powershell
  venv\Scripts\Activate.ps1
  ```
  > [!IMPORTANT]
  > **PowerShell Error Help**: If you get a red error saying `Script execution is disabled on this system`, PowerShell is blocking the activation script. Run this command to bypass it for your current window:
  > ```powershell
  > Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
  > ```
  > Then run `venv\Scripts\Activate.ps1` again.
* **If you are on Linux or macOS**:
  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

> [!NOTE]
> **Optional Speedups (`cryptg`)**: We have removed `cryptg` from the default dependencies to prevent compiler errors on Windows. The application works perfectly without it. If you want faster media downloading and have Microsoft C++ Build Tools installed, you can install the speedups by running:
> ```bash
> pip install .[speedups]
> ```

---

## 3. Quick Setup & Configuration

Configure the application in minutes without manually editing any configuration files:
```bash
python main.py setup
```

The wizard will guide you through:
1. **Choose Setup Mode**: Choose **Quick Setup** (Recommended) or **Advanced Setup**.
2. **API credentials**: Enter your Telegram API ID and API Hash (obtainable from [my.telegram.org](https://my.telegram.org) - see [Configuration Guide](CONFIGURATION.md)).
3. **Interactive Chat Picker**: Connects directly to Telegram so you can search and select your source and destination chats by name!
4. **Auto-Validation**: The wizard checks access and permissions, creating timestamped backups of any pre-existing configurations in `backups/`.

---

## 4. Verification & Troubleshooting

Verify that your installation is complete and ready to run:

### System Diagnostics Health Check
To run a diagnostics health check verifying permissions, networks, credentials, and state files:
```bash
python main.py doctor
```
If errors occur, the `doctor` command provides clear, step-by-step remediation actions.

### Validation Report
To run a configuration validation check:
```bash
python main.py validate
```

---

## 5. Docker Deployment

To run the forwarder inside a Docker container:

### 1. Configure configuration files locally
Generate your `.env` and `config.ini` files using the setup wizard on your host machine first:
```bash
python main.py setup
```

### 2. Start the Docker Container
Build and start the container in the background:
```bash
docker-compose up -d
```

### 3. Complete Telegram Authentication
If logging in for the first time, attach to the container to enter the verification code sent by Telegram:
```bash
docker attach telegram-forwarder
```
*Follow the prompts in your terminal to login. Press `Ctrl + P, Ctrl + Q` to detach from the container without stopping it.*
