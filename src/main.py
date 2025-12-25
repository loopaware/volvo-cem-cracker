#!/usr/bin/env python3
import json
import logging
from .utils import setup_logging
from .cracker.cem_cracker import CemCracker
from .notifier import EmailNotifier

def main():
    setup_logging()

    # Load Config
    config = {}
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        logging.warning("config.json not found. Email notifications disabled.")
    except json.JSONDecodeError:
        logging.error("Error decoding config.json. Email notifications disabled.")

    cracker = CemCracker()

    # Start Email Notifier
    email_notifier = None
    if config.get("email_notifications_enabled"):
        email_notifier = EmailNotifier(config.get("email_settings", {}), cracker)
        email_notifier.start()

    try:
        cracker.run()
    except KeyboardInterrupt:
        logging.info("Cracking process interrupted by user.")
    finally:
        if email_notifier:
            email_notifier.stop()

if __name__ == "__main__":
    main()
