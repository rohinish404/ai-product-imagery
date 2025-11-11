import os
import base64
import asyncio
import time
from typing import Optional
import requests
from io import BytesIO
from PIL import Image
from huggingface_hub import InferenceClient


class HuggingFaceService:
    def __init__(self, api_token: Optional[str] = None):
        if api_token is None:
            api_token = os.getenv("HUGGINGFACE_API_TOKEN")

        if not api_token:
            raise ValueError("HUGGINGFACE_API_TOKEN environment variable not set or api_token parameter not provided")

        self.api_token = api_token

        # Initialize the InferenceClient with the API token
        self.client = InferenceClient(api_key=self.api_token)

        # Use FLUX.1-dev model for better quality
        self.enhancement_model = "black-forest-labs/FLUX.1-dev"

        self.max_retries = 5
        self.base_delay = 3
        self.max_delay = 60
        self.throttle_delay = 2.0
        self._last_call_time = 0

    async def _throttle(self):
        current_time = time.time()
        time_since_last_call = current_time - self._last_call_time

        if time_since_last_call < self.throttle_delay:
            delay = self.throttle_delay - time_since_last_call
            print(f"Throttling HF API call, waiting {delay:.2f}s...")
            await asyncio.sleep(delay)

        self._last_call_time = time.time()

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("utf-8")
        return encoded

    async def _retry_with_backoff(self, func, *args, **kwargs):
        last_exception = None

        for attempt in range(self.max_retries):
            try:

                await self._throttle()

                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()


                is_rate_limit = (
                    "429" in error_str or
                    "503" in error_str or
                    "rate limit" in error_str or
                    "quota" in error_str or
                    "loading" in error_str or
                    "overloaded" in error_str or
                    "unavailable" in error_str
                )

                if is_rate_limit and attempt < self.max_retries - 1:

                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    print(f"HF API rate limit hit, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})...")
                    await asyncio.sleep(delay)
                    continue
                elif attempt < self.max_retries - 1:

                    delay = min(self.base_delay, self.max_delay)
                    print(f"HF API error occurred, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries}): {e}")
                    await asyncio.sleep(delay)
                    continue
                else:

                    break


        print(f"All HF API retry attempts failed: {last_exception}")
        raise last_exception

    async def enhance_product_image(
        self, image_path: str, product_name: str, background_style: str
    ) -> bytes:
        prompt = f"""Professional product photograph of {product_name}.
Place the product on {background_style}.
High quality commercial photography, professional studio lighting, sharp focus, clean presentation, 4K resolution."""

        print(f"DEBUG HF: Enhancing with prompt: {prompt[:100]}...")

        try:
            # Load the image
            with open(image_path, "rb") as img_file:
                image_bytes = img_file.read()

            img = Image.open(BytesIO(image_bytes))
            has_alpha = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)

            # For images with transparency, convert to RGB
            # FLUX.1-dev is a text-to-image model, not an inpainting model
            if has_alpha:
                print(f"DEBUG HF: Image has transparency, converting to RGB...")
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')

                # Convert to RGB with white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                img = background
            else:
                print(f"DEBUG HF: Image has no transparency, using as-is...")

            # Save processed image to BytesIO
            img_buffer = BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)

            # Define the API call function
            def _call_api():
                try:
                    # Use the InferenceClient's text_to_image method
                    result_image = self.client.text_to_image(
                        prompt=prompt,
                        model=self.enhancement_model,
                    )

                    # Convert PIL Image to bytes
                    output_buffer = BytesIO()
                    result_image.save(output_buffer, format='PNG')
                    return output_buffer.getvalue()

                except Exception as e:
                    error_msg = str(e)
                    print(f"DEBUG HF: API call error: {error_msg}")
                    raise Exception(f"HF API error: {error_msg}")

            # Use retry logic
            result = await self._retry_with_backoff(_call_api)

            print(f"DEBUG HF: Successfully enhanced image, received {len(result)} bytes")
            return result

        except Exception as e:
            print(f"Error enhancing image with HuggingFace: {e}")
            import traceback
            traceback.print_exc()
            return b""
