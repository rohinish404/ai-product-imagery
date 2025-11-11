import asyncio
from app.models.state import WorkflowState
from app.services.gemini_service import GeminiService


async def identify_products_node(state: WorkflowState) -> WorkflowState:
    print("DEBUG IDENTIFY: identify_products_node called (async)")
    extracted_frames = state.get("extracted_frames", [])

    print(f"DEBUG IDENTIFY: Got {len(extracted_frames)} extracted frames")

    if not extracted_frames:
        state["status"] = "error"
        state["error"] = "No frames available for analysis"
        return state

    try:
        gemini_service = GeminiService()


        state["current_step"] = "Identifying products with Gemini..."
        state["progress"] = 40

        products = await gemini_service.identify_products(extracted_frames)

        print(f"DEBUG: Found {len(products)} products: {products}")

        if not products:
            state["status"] = "error"
            state["error"] = "No products found in video"
            return state

        state["products"] = products


        state["current_step"] = "Selecting best frames with Gemini..."
        state["progress"] = 50

        best_frames = {}
        for idx, product in enumerate(products):
            product_name = product["name"]

            best_frame = await gemini_service.select_best_frame(
                extracted_frames, product_name
            )
            best_frames[product_name] = best_frame
            print(f"DEBUG: Best frame for {product_name}: {best_frame}")

        state["best_frames"] = best_frames
        state["current_step"] = f"Found {len(products)} product(s)"
        state["progress"] = 55

        print(f"DEBUG: best_frames dictionary: {best_frames}")

    except Exception as e:
        print(f"DEBUG IDENTIFY: Exception: {e}")
        import traceback
        traceback.print_exc()
        state["status"] = "error"
        state["error"] = f"Failed to identify products: {str(e)}"

    print(f"DEBUG IDENTIFY: identify_products_node returning, status={state.get('status')}")
    return state
