import base64
import os
import sys
import threading
import time

from dotenv import load_dotenv, set_key


class Spinner:
    """A fast spinner class to show progress."""

    busy = False
    delay = 0.05

    @staticmethod
    def spinning_cursor():
        while 1:
            for cursor in "|/-\\":
                yield cursor

    def __init__(self, message="Processing"):
        self.spinner_generator = self.spinning_cursor()
        self.message = message
        self.busy = False
        self.thread = None

    def spinner_task(self):
        while self.busy:
            sys.stdout.write(f"\r{self.message} {next(self.spinner_generator)}")
            sys.stdout.flush()
            time.sleep(self.delay)
        sys.stdout.write("\r" + " " * (len(self.message) + 2) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        self.busy = True
        self.thread = threading.Thread(target=self.spinner_task)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.busy = False
        if self.thread:
            self.thread.join()


def get_google_api_key():
    """Check and prompt for Google API key if not found."""
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not google_api_key:
        print("GOOGLE_API_KEY not found in .env file.")
        google_api_key = input("Please enter your Google API Key: ").strip()

        # Save the API key to .env file
        set_key(".env", "GOOGLE_API_KEY", google_api_key)
        os.environ["GOOGLE_API_KEY"] = google_api_key

    return google_api_key


def encode_image(image_path):
    """Encode an image to base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
