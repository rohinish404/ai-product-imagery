from langgraph.graph import StateGraph, END
from app.models.state import WorkflowState
from app.nodes.video_processing import download_video_node, extract_frames_node
from app.nodes.product_identification import identify_products_node
from app.nodes.segmentation import segment_products_node
from app.nodes.enhancement import enhance_products_node


def create_workflow() -> StateGraph:
    workflow = StateGraph(WorkflowState)

    workflow.add_node("download_video", download_video_node)
    workflow.add_node("extract_frames", extract_frames_node)
    workflow.add_node("identify_products", identify_products_node)
    workflow.add_node("segment_products", segment_products_node)
    workflow.add_node("enhance_products", enhance_products_node)

    workflow.set_entry_point("download_video")
    workflow.add_edge("download_video", "extract_frames")
    workflow.add_edge("extract_frames", "identify_products")
    workflow.add_edge("identify_products", "segment_products")
    workflow.add_edge("segment_products", "enhance_products")
    workflow.add_edge("enhance_products", END)

    return workflow.compile()


app = create_workflow()
