import asyncio
import uuid
from pathlib import Path
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from app.workflow import app as workflow_app
from app.models.state import WorkflowState


jobs: Dict[str, WorkflowState] = {}

router = APIRouter()


class VideoProcessRequest(BaseModel):
    youtube_url: HttpUrl


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    current_step: str
    progress: int
    error: Optional[str] = None


class JobResultsResponse(BaseModel):
    job_id: str
    status: str
    products: list
    best_frames: Dict[str, str]
    segmented_images: Dict[str, str]
    enhanced_images: Dict[str, list]
    segmentation_errors: Dict[str, str]
    enhancement_errors: Dict[str, str]


async def process_video_workflow(job_id: str, youtube_url: str):
    initial_state: WorkflowState = {
        "youtube_url": youtube_url,
        "job_id": job_id,
        "video_path": None,
        "extracted_frames": [],
        "products": [],
        "best_frames": {},
        "segmented_images": {},
        "segmentation_masks": {},
        "enhanced_images": {},
        "status": "processing",
        "current_step": "Starting...",
        "error": None,
        "progress": 0,
        "segmentation_errors": {},
        "enhancement_errors": {},
    }

    jobs[job_id] = initial_state

    try:
        print(f"DEBUG WORKFLOW: Starting workflow for job {job_id}")
        print(f"DEBUG WORKFLOW: Initial state: {initial_state.keys()}")

        result = await workflow_app.ainvoke(initial_state)

        print(f"DEBUG WORKFLOW: Workflow completed")
        print(f"DEBUG WORKFLOW: Result keys: {result.keys()}")
        print(f"DEBUG WORKFLOW: Status: {result.get('status')}")
        print(f"DEBUG WORKFLOW: Error: {result.get('error')}")
        print(f"DEBUG WORKFLOW: Products: {result.get('products')}")
        print(f"DEBUG WORKFLOW: Best frames: {result.get('best_frames')}")

        jobs[job_id] = result

    except Exception as e:
        print(f"DEBUG WORKFLOW: Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)


@router.post("/process-video", response_model=JobStatusResponse)
async def process_video(
    request: VideoProcessRequest, background_tasks: BackgroundTasks
) -> JobStatusResponse:
    job_id = str(uuid.uuid4())

    background_tasks.add_task(process_video_workflow, job_id, str(request.youtube_url))

    return JobStatusResponse(
        job_id=job_id,
        status="processing",
        current_step="Starting...",
        progress=0,
    )


@router.get("/job-status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    return JobStatusResponse(
        job_id=job_id,
        status=job.get("status", "unknown"),
        current_step=job.get("current_step", ""),
        progress=job.get("progress", 0),
        error=job.get("error"),
    )


@router.get("/results/{job_id}", response_model=JobResultsResponse)
async def get_job_results(job_id: str) -> JobResultsResponse:
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job.get("status") != "completed":
        raise HTTPException(
            status_code=400, detail="Job not completed yet or failed"
        )

    return JobResultsResponse(
        job_id=job_id,
        status=job["status"],
        products=job.get("products", []),
        best_frames=job.get("best_frames", {}),
        segmented_images=job.get("segmented_images", {}),
        enhanced_images=job.get("enhanced_images", {}),
        segmentation_errors=job.get("segmentation_errors", {}),
        enhancement_errors=job.get("enhancement_errors", {}),
    )


@router.get("/image/{job_id}/{image_type}/{filename}")
async def get_image(job_id: str, image_type: str, filename: str):
    image_path = Path(f"temp/{job_id}/{image_type}/{filename}")

    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(image_path)


@router.delete("/job/{job_id}")
async def delete_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    del jobs[job_id]

    job_dir = Path(f"temp/{job_id}")
    if job_dir.exists():
        import shutil

        shutil.rmtree(job_dir)

    return {"message": "Job deleted successfully"}
