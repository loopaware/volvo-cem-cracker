2025-12-25 12:40:00
## Objective: Implement robust logging, email notifications, and ensure connectivity checks.

## Tasks:
*   [ ] Refactor logging in `src/cracker.py` to use Python's `logging` module with rotation.
    *   Target log path: `/var/log/volvo-cracker/cracker.log` (prod) or `./cracker.log` (dev).
*   [ ] Implement `EmailNotifier` class in `src/cracker.py`.
    *   Use `smtplib` for Gmail SMTP.
    *   Load credentials from `config.json`.
    *   Run in a background thread, sending status updates periodically.
    *   Handle and log errors without crashing.
*   [ ] Ensure `check_connection` reads data and logs it (Verify existing logic).
*   [ ] Create `config.json` template.
*   [ ] Update Ansible playbook to create log directory and manage permissions.
*   [ ] Verify locally with simulated voltage sag and email mock.
