import os
import requests
from dotenv import load_dotenv
import json
import base64
from PIL import Image
from io import BytesIO
import io
from urllib.parse import urlparse
import threading
import cv2
import numpy as np

load_dotenv(override=True)

BLOCKED_DOMAINS = [
    "maliciousbook.com",
    "evilvideos.com",
    "darkwebforum.com",
    "shadytok.com",
    "suspiciouspins.com",
    "ilanbigio.com",
]


def pp(obj):
    print(json.dumps(obj, indent=4))


def show_image_cv2(base_64_image, timeout=2):
    """Display a base64-encoded PNG screenshot using OpenCV and close it after a timeout."""
    # Decode base64 to raw image bytes
    image_data = base64.b64decode(base_64_image)
    np_arr = np.frombuffer(image_data, np.uint8)

    # Decode the image from bytes into a numpy array (BGR format)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # Show image in an OpenCV window
    cv2.imshow("Screenshot", image)

    # Wait for timeout (converted to milliseconds)
    cv2.waitKey(timeout * 1000)

    # Close all OpenCV windows
    cv2.destroyAllWindows()

def show_image(base_64_image):
    image_data = base64.b64decode(base_64_image)
    image = Image.open(BytesIO(image_data))
    image.show()


def show_image_with_timeout(base_64_image, timeout=5):
    """Display an image and automatically close it after a set duration."""
    image_data = base64.b64decode(base_64_image)
    image = Image.open(BytesIO(image_data))
    image.show()

    # Close the image after the timeout
    def close_image():
        image.close()

    threading.Timer(timeout, close_image).start()


def calculate_image_dimensions(base_64_image):
    image_data = base64.b64decode(base_64_image)
    image = Image.open(io.BytesIO(image_data))
    return image.size


def sanitize_message(msg: dict) -> dict:
    """Return a copy of the message with image_url omitted for computer_call_output messages."""
    if msg.get("type") == "computer_call_output":
        output = msg.get("output", {})
        if isinstance(output, dict):
            sanitized = msg.copy()
            sanitized["output"] = {**output, "image_url": "[omitted]"}
            return sanitized
    return msg


def create_response(**kwargs):
    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }

    openai_org = os.getenv("OPENAI_ORG")
    if openai_org:
        headers["Openai-Organization"] = openai_org

    response = requests.post(url, headers=headers, json=kwargs)

    if response.status_code != 200:
        print(f"Error: {response.status_code} {response.text}")

    return response.json()


def check_blocklisted_url(url: str) -> None:
    """Raise ValueError if the given URL (including subdomains) is in the blocklist."""
    hostname = urlparse(url).hostname or ""
    if any(
        hostname == blocked or hostname.endswith(f".{blocked}")
        for blocked in BLOCKED_DOMAINS
    ):
        raise ValueError(f"Blocked URL: {url}")