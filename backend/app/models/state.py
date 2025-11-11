from typing import TypedDict, List, Dict, Optional


class WorkflowState(TypedDict):
    youtube_url: str
    job_id: str

    video_path: Optional[str]
    extracted_frames: List[str]

    products: List[Dict[str, str]]
    best_frames: Dict[str, str]

    segmented_images: Dict[str, str]
    segmentation_masks: Dict[str, str]

    enhanced_images: Dict[str, List[str]]

    status: str
    current_step: str
    error: Optional[str]
    progress: int

    segmentation_errors: Dict[str, str]
    enhancement_errors: Dict[str, str]
