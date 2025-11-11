import os
import base64
import json
import asyncio
import time
from typing import List, Dict, Tuple, Optional, Callable, Any
from google import genai
from google.genai.types import GenerateContentConfig, Part, ThinkingConfig


class GeminiService:
    def __init__(self, api_key: Optional[str] = None):
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set or api_key parameter not provided")

        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-flash"
        self.image_model = "gemini-2.5-flash-image"
        self.max_retries = 5
        self.base_delay = 3
        self.max_delay = 60
        self.throttle_delay = 2.5
        self._last_call_time = 0

    async def _throttle(self):
        current_time = time.time()
        time_since_last_call = current_time - self._last_call_time

        if time_since_last_call < self.throttle_delay:
            delay = self.throttle_delay - time_since_last_call
            print(f"Throttling API call, waiting {delay:.2f}s...")
            await asyncio.sleep(delay)

        self._last_call_time = time.time()

    async def _retry_with_backoff(
        self, func: Callable, *args, **kwargs
    ) -> Any:
        last_exception = None

        for attempt in range(self.max_retries):
            try:

                await self._throttle()

                return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()


                is_rate_limit = (
                    "429" in error_str or
                    "503" in error_str or
                    "rate limit" in error_str or
                    "quota" in error_str or
                    "resource exhausted" in error_str or
                    "overloaded" in error_str or
                    "unavailable" in error_str
                )

                if is_rate_limit and attempt < self.max_retries - 1:

                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    print(f"Rate limit hit, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})...")
                    await asyncio.sleep(delay)
                    continue
                elif attempt < self.max_retries - 1:

                    delay = min(self.base_delay, self.max_delay)
                    print(f"Error occurred, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries}): {e}")
                    await asyncio.sleep(delay)
                    continue
                else:

                    print(f"All retry attempts failed: {e}")
                    raise


        raise last_exception

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _create_image_part(self, image_path: str) -> Part:
        with open(image_path, "rb") as f:
            image_data = f.read()


        ext = image_path.lower().split(".")[-1]
        mime_types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
        }
        mime_type = mime_types.get(ext, "image/jpeg")

        return Part.from_bytes(data=image_data, mime_type=mime_type)

    async def identify_products(
        self, frame_paths: List[str]
    ) -> List[Dict[str, str]]:
        sample_frames = frame_paths[::max(len(frame_paths) // 10, 1)][:10]


        parts = [
            Part.from_text(text="""Analyze these video frames from a product review/unboxing video.

Your task:
1. Identify ALL distinct products shown in these frames
2. For each product, provide a name and brief description

Return your response as a JSON array with this structure:
[
  {
    "name": "Product Name",
    "description": "Brief description of the product"
  }
]

Only include actual products (not people, backgrounds, or generic items).
Be specific - for example, "iPhone 15 Pro" not just "phone".""")
        ]


        for frame_path in sample_frames:
            parts.append(self._create_image_part(frame_path))

        try:
            print(f"DEBUG GEMINI: Calling identify_products with {len(sample_frames)} frames")


            def _call_api():
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=parts,
                    config=GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.4,
                    ),
                )

            response = await self._retry_with_backoff(_call_api)

            print(f"DEBUG GEMINI: Got response: {response.text[:500]}")


            products = json.loads(response.text)
            print(f"DEBUG GEMINI: Parsed products: {products}")
            return products if isinstance(products, list) else []

        except Exception as e:
            print(f"Error identifying products: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def select_best_frame(
        self, frame_paths: List[str], product_name: str
    ) -> str:
        sample_frames = frame_paths[::max(len(frame_paths) // 20, 1)][:20]

        parts = [
            Part.from_text(text=f"""Analyze these video frames to find the best shot of: {product_name}

Your task:
1. Identify which frame shows the {product_name} most clearly and prominently
2. The product should be well-lit, in focus, and take up a good portion of the frame
3. Avoid frames where the product is partially obscured or blurry

Return a JSON object with:
{{
  "best_frame_index": <index number 0-{len(sample_frames)-1}>,
  "reason": "Brief explanation of why this frame is best"
}}""")
        ]


        for idx, frame_path in enumerate(sample_frames):
            parts.append(Part.from_text(text=f"\n--- Frame {idx} ---"))
            parts.append(self._create_image_part(frame_path))

        try:

            def _call_api():
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=parts,
                    config=GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.3,
                    ),
                )

            response = await self._retry_with_backoff(_call_api)

            result = json.loads(response.text)
            best_idx = result.get("best_frame_index", 0)


            if 0 <= best_idx < len(sample_frames):
                return sample_frames[best_idx]
            return sample_frames[0]

        except Exception as e:
            print(f"Error selecting best frame: {e}")
            return sample_frames[0] if sample_frames else frame_paths[0]

    async def segment_product(
        self, image_path: str, product_name: str
    ) -> Tuple[bytes, list]:
        parts = [
            Part.from_text(text=f"""Give the segmentation masks for the {product_name}. Output a JSON list of segmentation masks where each entry contains the 2D bounding box in the key "box_2d", the segmentation mask in key "mask", and the text label in the key "label". Use descriptive labels."""),
            self._create_image_part(image_path),
        ]

        try:
            print(f"DEBUG GEMINI: Calling segment_product for {product_name}")





            def _call_api():
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=parts,
                    config=GenerateContentConfig(
                        temperature=0.2,
                        thinking_config=ThinkingConfig(thinking_budget=0),
                        max_output_tokens=8192,
                    ),
                )

            response = await self._retry_with_backoff(_call_api)


            if not response or not response.text:
                print(f"DEBUG GEMINI: Empty or None response received")
                return b"", []

            print(f"DEBUG GEMINI: Segmentation response length: {len(response.text)}")
            print(f"DEBUG GEMINI: Segmentation response preview: {response.text[:500]}")


            response_text = response.text.strip()


            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()


            print(f"DEBUG GEMINI: Response text length after cleanup: {len(response_text)}")
            print(f"DEBUG GEMINI: First 1000 chars: {response_text[:1000]}")
            print(f"DEBUG GEMINI: Last 200 chars: {response_text[-200:]}")


            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as je:
                print(f"DEBUG GEMINI: JSON decode error: {je}")
                print(f"DEBUG GEMINI: Failed at position {je.pos}")
                print(f"DEBUG GEMINI: Context around error: {response_text[max(0, je.pos-100):min(len(response_text), je.pos+100)]}")
                return b"", []


            if isinstance(result, list) and len(result) > 0:
                result = result[0]

            mask_data = result.get("mask", "")
            box_2d = result.get("box_2d", [])

            print(f"DEBUG GEMINI: mask_data present: {bool(mask_data)}, length: {len(mask_data) if mask_data else 0}")
            if mask_data:
                print(f"DEBUG GEMINI: mask_data prefix (first 100 chars): {mask_data[:100]}")
            print(f"DEBUG GEMINI: box_2d: {box_2d}")


            if mask_data:
                try:

                    if mask_data.startswith("data:image/png;base64,"):
                        mask_data = mask_data[len("data:image/png;base64,"):]
                        print(f"DEBUG GEMINI: Stripped data URL prefix, new length: {len(mask_data)}")

                    mask_bytes = base64.b64decode(mask_data)
                    print(f"DEBUG GEMINI: Decoded mask to {len(mask_bytes)} bytes")
                    return mask_bytes, box_2d
                except Exception as e:
                    print(f"DEBUG GEMINI: Failed to decode mask: {e}")
                    import traceback
                    traceback.print_exc()
                    return b"", []
            else:
                return b"", []

        except Exception as e:
            print(f"Error segmenting product: {e}")
            import traceback
            traceback.print_exc()
            return b"", []

    async def enhance_product_image(
        self, image_path: str, product_name: str, background_style: str
    ) -> bytes:
        prompt = f"""Create a professional product photograph of this {product_name}.

Requirements:
- Place the product on {background_style}
- Ensure professional lighting and composition
- High quality, commercial photography style
- Sharp focus on the product
- Clean and attractive presentation"""

        parts = [
            Part.from_text(text=prompt),
            self._create_image_part(image_path),
        ]

        try:

            def _call_api():
                return self.client.models.generate_content(
                    model=self.image_model,
                    contents=parts,
                    config=GenerateContentConfig(
                        temperature=0.7,
                    ),
                )

            response = await self._retry_with_backoff(_call_api)


            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, "inline_data") and part.inline_data:
                            return part.inline_data.data

            return b""

        except Exception as e:
            print(f"Error enhancing image: {e}")
            import traceback
            traceback.print_exc()
            return b""
