2025-12-25 12:40:00
## Objective: Implement robust logging, email notifications, and ensure connectivity checks.

## Tasks:
*   [x] Refactor logging in `src/cracker.py` to use Python's `logging` module with rotation.
    *   Target log path: `/var/log/volvo-cracker/cracker.log` (prod) or `./cracker.log` (dev).
*   [x] Implement `EmailNotifier` class in `src/cracker.py`.
    *   Use `smtplib` for Gmail SMTP.
    *   Load credentials from `config.json`.
    *   Run in a background thread, sending status updates periodically.
    *   Handle and log errors without crashing.
*   [x] Ensure `check_connection` reads data and logs it (Verify existing logic).
*   [x] Create `config.json` template.
*   [x] Update Ansible playbook to create log directory and manage permissions.
*   [x] Verify locally with simulated voltage sag and email mock.