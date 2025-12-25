import smtplib
import threading
import logging

class EmailNotifier(threading.Thread):
    def __init__(self, config, cracker_instance):
        super().__init__()
        self.config = config
        self.cracker = cracker_instance
        self.stop_event = threading.Event()
        self.daemon = True

    def send_email(self, subject, body):
        if not all([self.config.get('smtp_server'), self.config.get('smtp_port'), self.config.get('username'), self.config.get('password'), self.config.get('recipient')]):
            logging.warning("Email config incomplete. Skipping email notification.")
            return

        try:
            server = smtplib.SMTP_SSL(self.config['smtp_server'], self.config['smtp_port'])
            server.login(self.config['username'], self.config['password'])
            
            message = f"Subject: {subject}\n\n{body}"
            server.sendmail(self.config['username'], self.config['recipient'], message)
            server.quit()
            logging.info(f"Email notification sent: {subject}")
        except Exception as e:
            logging.error(f"Failed to send email: {e}")

    def run(self):
        self.send_email("Volvo Cracker Status", "Cracking process started.")
        
        while not self.stop_event.wait(self.config.get('update_interval', 3600)):
            # This is where you'd fetch the current status from the cracker
            # For now, we'll just send a generic message.
            status_message = "Cracking is in progress."
            self.send_email("Volvo Cracker Status Update", status_message)
            
        self.send_email("Volvo Cracker Status", "Cracking process stopped.")

    def stop(self):
        self.stop_event.set()
