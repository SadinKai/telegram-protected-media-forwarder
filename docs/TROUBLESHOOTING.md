# Troubleshooting Guide

This guide contains solutions to common problems and errors you might encounter when using **telegram-protected-media-forwarder**.

> [!WARNING]
> **CRITICAL SECURITY WARNING**: The `.sessions/` folder (specifically `.sessions/forwarder.session`) contains your Telegram login session keys. Anyone who has access to these files can fully control your Telegram account! **NEVER** share your session files, API ID, or API Hash with anyone, or post them online.

---

## 1. Diagnostics with the `doctor` command

The central entry point for troubleshooting is the `doctor` command:

```bash
python main.py doctor
```

It runs an exhaustive health check verification:
- API credentials configuration syntax.
- Session file read/write permissions.
- Telegram network server connectivity.
- Source and Destination chat access.
- Destination send/post privileges.
- State registry file health.
- Download directory permissions.

If any issues are found, the doctor command provides a numbered list of suggested actions to resolve them.

---

## 2. Common Errors and Resolutions

### Error: `Telegram connection failed`
- **Likely Cause**: Blocked by network, VPN disconnected, or invalid credentials.
- **Smart Actions**:
  1. Check your internet connection or try using a mobile hotspot.
  2. Verify that your API keys are correct.
  3. Re-run setup: `python main.py setup`.

### Error: `Destination chat inaccessible / send permissions failed`
- **Likely Cause**: You are not a member of the destination chat, you do not have permissions to post messages (e.g. read-only channel or group restrictions), or the chat ID is incorrect.
- **Smart Actions**:
  1. Run `python main.py list-chats` and verify the destination chat's ACCESS column says `Read/Write`.
  2. Confirm your membership and admin rights in the chat using your official Telegram client.

### Error: `sqlite3.OperationalError: database is locked`
- **Likely Cause**: Another instance of the application is running and using the same session file.
- **Smart Actions**:
  - Close any other running instances of the forwarder.

### Error: `State file registry is corrupted`
- **Likely Cause**: The registry JSON was manually edited or interrupted mid-write.
- **Smart Actions**:
  - Reset offsets for all configured jobs to start fresh:
    ```bash
    python main.py reset-offset --all
    ```
