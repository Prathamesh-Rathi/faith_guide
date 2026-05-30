import requests
import urllib.parse
import re
import os
import time
import base64
from config import Config


CHRISTIAN_STYLE_GUIDE = (
    "beautiful Christian religious art, spiritual and reverent, "
    "painterly style, warm golden divine light, sacred holy atmosphere, "
    "masterpiece quality digital painting, detailed, cinematic lighting"
)

NEGATIVE_PROMPT = (
    "nsfw, nude, violent, gore, dark, evil, satanic, demonic, "
    "blurry, low quality, distorted, ugly, watermark"
)

BLOCKED_IMAGE_THEMES = [
    r'naked|nude|sexual|explicit|nsfw',
    r'satan|devil|demon|666|lucifer|antichrist',
    r'gore|blood|violent|murder|torture',
    r'mock(ing)?\s+(jesus|god|christ|bible|church)',
    r'heretical|blasphemous|sacrilegious',
    r'real\s+person|actual\s+person',
]

SUBTLE_VIOLATIONS = [
    r'jesus\s+(holding|with|next\s+to)\s+(gun|weapon)',
    r'bible\s+(burning|destroyed|torn)',
    r'cross\s+(burning|on\s+fire)',
]


def check_image_prompt(prompt: str) -> dict:
    prompt_lower = prompt.lower()

    for pattern in BLOCKED_IMAGE_THEMES:
        if re.search(pattern, prompt_lower, re.IGNORECASE):
            return {
                "safe":        False,
                "reason":      "This image prompt contains content that cannot be generated.",
                "safe_prompt": ""
            }

    for pattern in SUBTLE_VIOLATIONS:
        if re.search(pattern, prompt_lower, re.IGNORECASE):
            return {
                "safe":        False,
                "reason":      "This prompt contains a policy violation.",
                "safe_prompt": ""
            }

    safe_prompt = f"{prompt}, {CHRISTIAN_STYLE_GUIDE}"
    return {
        "safe":        True,
        "reason":      "Prompt passed safety checks",
        "safe_prompt": safe_prompt
    }


# ── Method 1: Hugging Face Inference API ─────────────────────────────────────
def generate_via_huggingface(safe_prompt: str) -> dict:
    """
    Generate image using Hugging Face free inference API.
    Returns {success, image_b64, error}
    """
    headers = {
        "Authorization": f"Bearer {Config.HF_API_KEY}",
        "Content-Type":  "application/json"
    }

    payload = {
        "inputs": safe_prompt,
        "parameters": {
            "negative_prompt": NEGATIVE_PROMPT,
            "num_inference_steps": 20,
            "guidance_scale":      7.5,
            "width":               768,
            "height":              512,
        }
    }

    try:
        response = requests.post(
            Config.HF_MODEL_URL,
            headers = headers,
            json    = payload,
            timeout = 60
        )

        # Model loading — wait and retry once
        if response.status_code == 503:
            print("HF model loading, waiting 20s...")
            time.sleep(20)
            response = requests.post(
                Config.HF_MODEL_URL,
                headers = headers,
                json    = payload,
                timeout = 60
            )

        if response.status_code == 200:
            # Response is raw image bytes
            img_b64 = base64.b64encode(response.content).decode('utf-8')
            return {
                "success":   True,
                "image_b64": img_b64,
                "error":     None
            }

        error_msg = response.json() if response.content else {}
        return {
            "success":   False,
            "image_b64": "",
            "error":     f"HF API error {response.status_code}: {error_msg}"
        }

    except requests.exceptions.Timeout:
        return {
            "success":   False,
            "image_b64": "",
            "error":     "Hugging Face request timed out"
        }
    except Exception as e:
        return {
            "success":   False,
            "image_b64": "",
            "error":     str(e)
        }


# ── Method 2: Pollinations AI (fallback) ─────────────────────────────────────
def generate_via_pollinations(safe_prompt: str) -> dict:
    """
    Fallback image generation via Pollinations.ai.
    Returns {success, image_url, error}
    """
    try:
        encoded   = urllib.parse.quote(safe_prompt)
        image_url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=768&height=512&nologo=true&seed={int(time.time())}"
        )

        # Poll until image is ready (max 60 seconds)
        for attempt in range(6):
            try:
                resp = requests.get(image_url, timeout=15, stream=True)
                if resp.status_code == 200:
                    content_type = resp.headers.get('content-type', '')
                    if 'image' in content_type:
                        return {
                            "success":   True,
                            "image_url": image_url,
                            "error":     None
                        }
            except Exception:
                pass
            print(f"Pollinations attempt {attempt + 1}/6 — waiting...")
            time.sleep(10)

        return {
            "success":   False,
            "image_url": image_url,
            "error":     "Pollinations did not return image in time"
        }

    except Exception as e:
        return {
            "success":   False,
            "image_url": "",
            "error":     str(e)
        }


# ── Method 3: Save base64 image to static folder ─────────────────────────────
def save_image_locally(image_b64: str, prompt: str) -> str:
    """
    Save a base64 image to app/static/images/ and return the path.
    """
    try:
        # Create directory if needed
        save_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'static', 'images', 'generated'
        )
        os.makedirs(save_dir, exist_ok=True)

        # Unique filename from timestamp
        filename  = f"faith_{int(time.time())}.png"
        filepath  = os.path.join(save_dir, filename)
        image_url = f"/static/images/generated/{filename}"

        # Decode and save
        img_bytes = base64.b64decode(image_b64)
        with open(filepath, 'wb') as f:
            f.write(img_bytes)

        return image_url

    except Exception as e:
        print(f"Failed to save image locally: {e}")
        return ""


# ── Main generation function ──────────────────────────────────────────────────
def generate_christian_image(prompt: str, user_id: int = None) -> dict:
    """
    Generate image with automatic fallback:
    1. Try Hugging Face (best quality)
    2. Fall back to Pollinations if HF fails

    Returns:
    {
        success:    bool,
        image_url:  str,   (local path or external URL)
        safe_prompt: str,
        error:      str or None
    }
    """
    # Safety check first
    check = check_image_prompt(prompt)
    if not check["safe"]:
        return {
            "success":    False,
            "image_url":  "",
            "safe_prompt": "",
            "error":      check["reason"]
        }

    safe_prompt = check["safe_prompt"]
    image_url   = ""

    # ── Try Hugging Face first ────────────────────────────────────────────────
    hf_key = Config.HF_API_KEY
    if hf_key and hf_key != 'your-hf-token-here':
        print("Trying Hugging Face...")
        hf_result = generate_via_huggingface(safe_prompt)

        if hf_result["success"]:
            # Save base64 image to local static folder
            image_url = save_image_locally(hf_result["image_b64"], prompt)
            if image_url:
                print(f"HF image saved: {image_url}")
            else:
                hf_result["success"] = False

    # ── Fall back to Pollinations ─────────────────────────────────────────────
    if not image_url:
        print("Falling back to Pollinations...")
        poll_result = generate_via_pollinations(safe_prompt)
        if poll_result["success"]:
            image_url = poll_result["image_url"]
        else:
            return {
                "success":    False,
                "image_url":  "",
                "safe_prompt": safe_prompt,
                "error":      "Both image generation methods failed. Please try again."
            }

    # ── Save to DB ────────────────────────────────────────────────────────────
    if user_id and image_url:
        try:
            from app import db
            from app.models import GeneratedImage
            img = GeneratedImage(
                user_id     = user_id,
                prompt      = prompt,
                safe_prompt = safe_prompt,
                image_url   = image_url
            )
            db.session.add(img)
            db.session.commit()
        except Exception as e:
            print(f"DB save failed: {e}")

    return {
        "success":    True,
        "image_url":  image_url,
        "safe_prompt": safe_prompt,
        "error":      None
    }


def suggest_christian_image_prompts() -> list:
    return [
        "Jesus walking on water at sunrise",
        "The Good Shepherd carrying a lamb in golden fields",
        "A dove descending with rays of light through clouds",
        "The empty tomb on Easter morning with blooming flowers",
        "A humble prayer in a candlelit chapel",
        "The Last Supper painted in Renaissance style",
        "Noah's ark resting on Mount Ararat at sunset",
        "Angels gathered around a glowing manger in Bethlehem",
        "A cross on a hilltop silhouetted against a purple sky",
        "Moses parting the Red Sea with divine light",
    ]