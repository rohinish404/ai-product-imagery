import os
import cv2
from pathlib import Path
from typing import List
import yt_dlp
from app.models.state import WorkflowState


def download_video_node(state: WorkflowState) -> WorkflowState:
    print("DEBUG VIDEO: download_video_node called")
    youtube_url = state["youtube_url"]
    job_id = state["job_id"]
    print(f"DEBUG VIDEO: URL={youtube_url}, job_id={job_id}")

    output_dir = Path(f"temp/{job_id}")
    output_dir.mkdir(parents=True, exist_ok=True)

    video_path = str(output_dir / "video.mp4")

    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": video_path,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

        print(f"DEBUG VIDEO: Video downloaded to {video_path}")
        state["video_path"] = video_path
        state["status"] = "processing"
        state["current_step"] = "Video downloaded"
        state["progress"] = 20

    except Exception as e:
        print(f"DEBUG VIDEO: Error downloading: {e}")
        state["status"] = "error"
        state["error"] = f"Failed to download video: {str(e)}"
        state["progress"] = 0

    print(f"DEBUG VIDEO: download_video_node returning, status={state['status']}")
    return state


def extract_frames_node(state: WorkflowState) -> WorkflowState:
    print("DEBUG FRAMES: extract_frames_node called")
    video_path = state.get("video_path")
    job_id = state["job_id"]

    print(f"DEBUG FRAMES: video_path={video_path}, exists={os.path.exists(video_path) if video_path else False}")

    if not video_path or not os.path.exists(video_path):
        print("DEBUG FRAMES: Error - video file not found")
        state["status"] = "error"
        state["error"] = "Video file not found"
        return state

    frames_dir = Path(f"temp/{job_id}/frames")
    frames_dir.mkdir(parents=True, exist_ok=True)

    try:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        frame_interval = max(int(fps), 1)
        max_frames = 120

        extracted_frames = []
        frame_count = 0
        saved_count = 0

        while cap.isOpened() and saved_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                frame_path = frames_dir / f"frame_{saved_count:04d}.jpg"
                cv2.imwrite(str(frame_path), frame)
                extracted_frames.append(str(frame_path))
                saved_count += 1

            frame_count += 1

        cap.release()

        print(f"DEBUG FRAMES: Extracted {len(extracted_frames)} frames")
        state["extracted_frames"] = extracted_frames
        state["status"] = "processing"
        state["current_step"] = f"Extracted {len(extracted_frames)} frames"
        state["progress"] = 30

    except Exception as e:
        print(f"DEBUG FRAMES: Error: {e}")
        state["status"] = "error"
        state["error"] = f"Failed to extract frames: {str(e)}"

    print(f"DEBUG FRAMES: extract_frames_node returning, frames count={len(state.get('extracted_frames', []))}")
    return state
