import re
from pathlib import Path
from PIL import Image
import io
import numpy as np
from app.models.state import WorkflowState
from app.services.gemini_service import GeminiService


def sanitize_filename(name: str) -> str:
    name = name.replace(" ", "_")

    name = re.sub(r'[()\/\\:*?"<>|]', '', name)

    name = re.sub(r'_+', '_', name)

    name = name.strip('_')
    return name


async def segment_products_node(state: WorkflowState) -> WorkflowState:
    best_frames = state.get("best_frames", {})
    job_id = state["job_id"]

    print(f"DEBUG SEGMENTATION: Received best_frames: {best_frames}")
    print(f"DEBUG SEGMENTATION: Number of frames: {len(best_frames)}")

    if not best_frames:
        state["status"] = "error"
        state["error"] = "No frames available for segmentation"
        print("DEBUG SEGMENTATION: ERROR - No best_frames!")
        return state

    try:
        gemini_service = GeminiService()


        output_dir = Path(f"temp/{job_id}/segmented")
        output_dir.mkdir(parents=True, exist_ok=True)

        segmented_images = {}
        segmentation_masks = {}
        segmentation_errors = {}

        state["current_step"] = "Segmenting products with Gemini 2.5..."
        state["progress"] = 60

        for product_name, frame_path in best_frames.items():
            print(f"DEBUG SEGMENTATION: Processing {product_name} from {frame_path}")

            try:

                mask_bytes, bbox = await gemini_service.segment_product(
                    frame_path, product_name
                )

                print(f"DEBUG SEGMENTATION: Got mask_bytes length: {len(mask_bytes) if mask_bytes else 0}")

                if mask_bytes:
                    try:

                        safe_name = sanitize_filename(product_name)
                        mask_path = output_dir / f"{safe_name}_mask.png"

                        print(f"DEBUG SEGMENTATION: Received mask_bytes length: {len(mask_bytes)}")


                        with open(mask_path, "wb") as f:
                            f.write(mask_bytes)
                        print(f"DEBUG SEGMENTATION: Saved mask to {mask_path}")

                        segmentation_masks[product_name] = str(mask_path)


                        print(f"DEBUG SEGMENTATION: Applying mask to image...")
                        segmented_path = apply_mask_to_image(
                            frame_path, mask_bytes, output_dir, product_name
                        )
                        segmented_images[product_name] = segmented_path
                        print(f"DEBUG SEGMENTATION: Segmented {product_name} -> {segmented_path}")
                    except Exception as e:
                        error_msg = f"Failed to process mask: {str(e)}"
                        print(f"DEBUG SEGMENTATION: Error processing mask for {product_name}: {e}")
                        segmentation_errors[product_name] = error_msg
                        import traceback
                        traceback.print_exc()
                else:
                    error_msg = "No segmentation mask returned from Gemini"
                    print(f"DEBUG SEGMENTATION: WARNING - {error_msg} for {product_name}")
                    segmentation_errors[product_name] = error_msg
            except Exception as e:
                error_msg = f"Segmentation failed: {str(e)}"
                print(f"DEBUG SEGMENTATION: Exception for {product_name}: {e}")
                segmentation_errors[product_name] = error_msg
                import traceback
                traceback.print_exc()

        print(f"DEBUG SEGMENTATION: Final segmented_images: {segmented_images}")
        print(f"DEBUG SEGMENTATION: Total segmented: {len(segmented_images)}")
        print(f"DEBUG SEGMENTATION: Segmentation errors: {segmentation_errors}")

        state["segmented_images"] = segmented_images
        state["segmentation_masks"] = segmentation_masks
        state["segmentation_errors"] = segmentation_errors


        success_count = len(segmented_images)
        error_count = len(segmentation_errors)
        if success_count > 0:
            state["current_step"] = f"Segmented {success_count} product(s)" + (f" ({error_count} failed)" if error_count > 0 else "")
        else:
            state["current_step"] = "Segmentation failed for all products"

        state["progress"] = 70

    except Exception as e:
        print(f"DEBUG SEGMENTATION: Main exception: {e}")
        import traceback
        traceback.print_exc()
        state["status"] = "error"
        state["error"] = f"Failed to segment products: {str(e)}"
        state["segmentation_errors"] = {}

    print(f"DEBUG SEGMENTATION: Returning state, status={state.get('status')}")
    return state


def apply_mask_to_image(
    image_path: str, mask_bytes: bytes, output_dir: Path, product_name: str
) -> str:
    print(f"DEBUG APPLY_MASK: Starting for {product_name}")
    print(f"DEBUG APPLY_MASK: image_path={image_path}, mask_bytes length={len(mask_bytes)}")


    print(f"DEBUG APPLY_MASK: Loading original image...")
    original_img = Image.open(image_path).convert("RGBA")
    print(f"DEBUG APPLY_MASK: Original image size: {original_img.size}")


    print(f"DEBUG APPLY_MASK: Loading mask image...")
    mask_img = Image.open(io.BytesIO(mask_bytes)).convert("L")
    print(f"DEBUG APPLY_MASK: Mask image size: {mask_img.size}")


    if mask_img.size != original_img.size:
        print(f"DEBUG APPLY_MASK: Resizing mask from {mask_img.size} to {original_img.size}")
        mask_img = mask_img.resize(original_img.size, Image.Resampling.LANCZOS)


    print(f"DEBUG APPLY_MASK: Converting to numpy arrays...")
    mask_array = np.array(mask_img)


    img_array = np.array(original_img)

    print(f"DEBUG APPLY_MASK: Image array shape: {img_array.shape}")


    if len(img_array.shape) == 3:

        if img_array.shape[2] == 3:
            print(f"DEBUG APPLY_MASK: Adding alpha channel...")
            alpha = np.ones((img_array.shape[0], img_array.shape[1]), dtype=np.uint8) * 255
            img_array = np.dstack((img_array, alpha))


    print(f"DEBUG APPLY_MASK: Applying mask to alpha channel...")
    img_array[:, :, 3] = mask_array


    print(f"DEBUG APPLY_MASK: Creating result image...")
    result_img = Image.fromarray(img_array, mode="RGBA")


    print(f"DEBUG APPLY_MASK: Cropping to bounding box...")
    bbox = result_img.getbbox()
    if bbox:
        result_img = result_img.crop(bbox)
        print(f"DEBUG APPLY_MASK: Cropped to bbox: {bbox}")


    safe_name = sanitize_filename(product_name)
    output_path = output_dir / f"{safe_name}_segmented.png"
    print(f"DEBUG APPLY_MASK: Saving to {output_path}")
    result_img.save(output_path, "PNG")

    print(f"DEBUG APPLY_MASK: Complete!")
    return str(output_path)
