import os
import re
from pathlib import Path
from app.models.state import WorkflowState
from app.services.huggingface_service import HuggingFaceService


def sanitize_filename(name: str) -> str:
    name = name.replace(" ", "_")

    name = re.sub(r'[()\/\\:*?"<>|]', '', name)

    name = re.sub(r'_+', '_', name)

    name = name.strip('_')
    return name



BACKGROUND_STYLES = [
    "a clean white studio background with soft shadows and professional lighting",
    "a modern minimalist desk setup with natural wood texture",
    "a gradient background transitioning from deep purple to electric blue",
]


async def enhance_products_node(state: WorkflowState) -> WorkflowState:
    print("DEBUG ENHANCEMENT: enhance_products_node called")
    segmented_images = state.get("segmented_images", {})
    job_id = state["job_id"]

    print(f"DEBUG ENHANCEMENT: Received {len(segmented_images)} segmented images")
    print(f"DEBUG ENHANCEMENT: segmented_images keys: {list(segmented_images.keys())}")

    if not segmented_images:
        state["status"] = "error"
        state["error"] = "No segmented images available for enhancement"
        return state

    try:

        hf_api_token = os.getenv("HUGGINGFACE_API_TOKEN")
        if hf_api_token:
            print(f"DEBUG ENHANCEMENT: Using HUGGINGFACE_API_TOKEN (ends with ...{hf_api_token[-4:]})")
        else:
            print("DEBUG ENHANCEMENT: HUGGINGFACE_API_TOKEN not found!")

        hf_service = HuggingFaceService(api_token=hf_api_token)


        output_dir = Path(f"temp/{job_id}/enhanced")
        output_dir.mkdir(parents=True, exist_ok=True)

        enhanced_images = {}
        enhancement_errors = {}

        state["current_step"] = "Enhancing product images with Stable Diffusion..."
        state["progress"] = 75

        for product_name, segmented_path in segmented_images.items():
            product_enhanced = []
            product_errors = []


            for idx, background_style in enumerate(BACKGROUND_STYLES[:3]):
                try:
                    state["current_step"] = (
                        f"Enhancing {product_name} (style {idx + 1}/3)..."
                    )


                    enhanced_bytes = await hf_service.enhance_product_image(
                        segmented_path, product_name, background_style
                    )

                    if enhanced_bytes:

                        safe_name = sanitize_filename(product_name)
                        output_path = (
                            output_dir
                            / f"{safe_name}_enhanced_{idx + 1}.png"
                        )

                        with open(output_path, "wb") as f:
                            f.write(enhanced_bytes)

                        product_enhanced.append(str(output_path))
                    else:
                        error_msg = f"Style {idx + 1}: No image returned (possibly rate limited)"
                        product_errors.append(error_msg)
                        print(f"DEBUG ENHANCEMENT: {error_msg} for {product_name}")
                except Exception as e:
                    error_msg = f"Style {idx + 1}: {str(e)}"
                    product_errors.append(error_msg)
                    print(f"DEBUG ENHANCEMENT: Error enhancing {product_name} style {idx + 1}: {e}")
                    import traceback
                    traceback.print_exc()


            if product_enhanced:
                enhanced_images[product_name] = product_enhanced
            if product_errors:
                enhancement_errors[product_name] = "; ".join(product_errors)

        state["enhanced_images"] = enhanced_images
        state["enhancement_errors"] = enhancement_errors


        total_products = len(segmented_images)
        enhanced_count = len(enhanced_images)
        error_count = len(enhancement_errors)

        print(f"DEBUG ENHANCEMENT: Enhanced {enhanced_count}/{total_products} products")
        print(f"DEBUG ENHANCEMENT: Enhancement errors: {enhancement_errors}")

        state["status"] = "completed"
        if enhanced_count > 0:
            state["current_step"] = "Processing complete!" + (f" ({error_count} products had enhancement issues)" if error_count > 0 else "")
        else:
            state["current_step"] = "Processing complete (enhancement failed for all products)"

        state["progress"] = 100

    except Exception as e:
        print(f"DEBUG ENHANCEMENT: Exception: {e}")
        import traceback
        traceback.print_exc()
        state["status"] = "error"
        state["error"] = f"Failed to enhance images: {str(e)}"
        state["enhancement_errors"] = {}

    print(f"DEBUG ENHANCEMENT: Returning state, status={state.get('status')}")
    return state
