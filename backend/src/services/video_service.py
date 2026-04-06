"""
Video service - handles video processing business logic.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Awaitable, Tuple
import logging
import json
import subprocess

from ..utils.async_helpers import run_in_thread
from ..youtube_utils import (
    async_download_youtube_video,
    async_get_youtube_video_info,
    async_get_youtube_video_title,
    get_youtube_video_id,
)
from ..video_utils import (
    get_video_transcript,
    create_clips_with_transitions,
    create_optimized_clip,
    parse_timestamp_to_seconds,
    detect_webcam_region,
)
from ..ai import get_most_relevant_parts_by_transcript
from ..config import Config

logger = logging.getLogger(__name__)
config = Config()
UPLOAD_URL_PREFIX = "upload://"


class VideoService:
    """Service for video processing operations."""

    @staticmethod
    async def get_preview_frame(url: str) -> Optional[str]:
        """
        Fetch a preview frame from a video URL (YouTube or local).
        Returns base64 data URL.
        """
        video_id = get_youtube_video_id(url)
        if video_id:
            # For YouTube, use our optimized extraction
            from ..youtube_utils import get_youtube_preview_frame
            return await get_youtube_preview_frame(url)
        
        # For local files/uploads, we could implement similar logic if needed,
        # but the frontend already handles local file previews.
        return None

    @staticmethod
    def _get_file_duration(path: Path) -> Optional[float]:
        """Return video duration in seconds via ffprobe, or None on failure."""
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "csv=p=0",
                    str(path),
                ],
                capture_output=True, text=True, check=True,
            )
            return float(result.stdout.strip())
        except Exception:
            return None

    @staticmethod
    def resolve_local_video_path(url: str) -> Path:
        """Resolve uploaded-video references without exposing server filesystem paths."""
        if url.startswith(UPLOAD_URL_PREFIX):
            filename = Path(url.removeprefix(UPLOAD_URL_PREFIX)).name
            return Path(config.temp_dir) / "uploads" / filename
        return Path(url)

    @staticmethod
    async def download_video(url: str, task_id: Optional[str] = None, quality: str = "high") -> Optional[Path]:
        """
        Download a YouTube video asynchronously.
        """
        logger.info(f"Starting video download: {url} (quality: {quality})")
        video_path = await async_download_youtube_video(url, 3, task_id, skip_if_exists=True, quality=quality)

        if not video_path:
            logger.error(f"Failed to download video: {url}")
            return None

        logger.info(f"Video downloaded successfully: {video_path}")
        return video_path

    @staticmethod
    async def split_video_into_segments(
        video_path: Path,
        segment_duration: float = 5400.0,
    ) -> List[Tuple[Path, float, float]]:
        """
        Split a video into segments if it exceeds segment_duration.
        Returns a list of (segment_path, start_time_offset, end_time_offset).
        """
        duration = VideoService._get_file_duration(video_path)
        if not duration or duration <= segment_duration:
            return [(video_path, 0.0, duration or 0.0)]

        logger.info(f"Video duration ({duration}s) exceeds segment limit ({segment_duration}s). Splitting...")
        
        segments = []
        num_segments = int(duration // segment_duration) + (1 if duration % segment_duration > 0 else 0)
        
        for i in range(num_segments):
            start = i * segment_duration
            end = min((i + 1) * segment_duration, duration)
            segment_path = video_path.parent / f"{video_path.stem}_part{i+1}{video_path.suffix}"
            
            # Use ffmpeg -ss before -i for fast seeking, though it may be less precise
            # For 90-min chunks, this is usually acceptable.
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start),
                "-t", str(end - start),
                "-i", str(video_path),
                "-c", "copy",
                "-avoid_negative_ts", "make_zero",
                str(segment_path)
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                segments.append((segment_path, start, end))
                logger.info(f"Created segment {i+1}: {start}s to {end}s -> {segment_path.name}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to split segment {i+1}: {e.stderr.decode()}")
                if i == 0:
                    return [(video_path, 0.0, duration)]
        
        return segments

    @staticmethod
    async def get_video_title(url: str) -> str:
        """
        Get video title asynchronously.
        Returns a default title if retrieval fails.
        """
        try:
            title = await async_get_youtube_video_title(url)
            return title or "YouTube Video"
        except Exception as e:
            logger.warning(f"Failed to get video title: {e}")
            return "YouTube Video"

    @staticmethod
    async def generate_transcript(
        video_path: Path, processing_mode: str = "balanced"
    ) -> str:
        """
        Generate transcript from video using AssemblyAI.
        Runs in thread pool to avoid blocking.
        """
        logger.info(f"Generating transcript for: {video_path}")
        speech_model = "best"
        if processing_mode == "fast":
            speech_model = config.fast_mode_transcript_model

        transcript = await run_in_thread(get_video_transcript, video_path, speech_model)
        logger.info(f"Transcript generated: {len(transcript)} characters")
        return transcript

    @staticmethod
    async def analyze_transcript(transcript: str) -> Any:
        """
        Analyze transcript with AI to find relevant segments.
        This is already async, no need to wrap.
        """
        logger.info("Starting AI analysis of transcript")
        relevant_parts = await get_most_relevant_parts_by_transcript(transcript)
        logger.info(
            f"AI analysis complete: {len(relevant_parts.most_relevant_segments)} segments found"
        )
        return relevant_parts

    @staticmethod
    async def create_video_clips(
        video_path: Path,
        segments: List[Dict[str, Any]],
        font_family: str = "TikTokSans-Regular",
        font_size: int = 24,
        font_color: str = "#FFFFFF",
        caption_template: str = "default",
        output_format: str = "vertical",
        add_subtitles: bool = True,
        webcam_box: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Create standalone video clips from segments with optional subtitles.
        Runs in thread pool as video processing is CPU-intensive.
        output_format: 'vertical' (9:16) or 'original' (keep source size, faster).
        add_subtitles: False skips subtitles; with original format uses ffmpeg stream copy (no re-encode).
        """
        logger.info(f"Creating {len(segments)} video clips subtitles={add_subtitles}")
        clips_output_dir = Path(config.temp_dir) / "clips"
        clips_output_dir.mkdir(parents=True, exist_ok=True)

        clips_info = await run_in_thread(
            create_clips_with_transitions,
            video_path,
            segments,
            clips_output_dir,
            font_family,
            font_size,
            font_color,
            caption_template,
            output_format,
            add_subtitles,
            webcam_box,
        )

        logger.info(f"Successfully created {len(clips_info)} clips")
        return clips_info

    @staticmethod
    async def create_single_clip(
        video_path: Path,
        segment: Dict[str, Any],
        clip_index: int,
        output_dir: Path,
        font_family: str = "TikTokSans-Regular",
        font_size: int = 24,
        font_color: str = "#FFFFFF",
        caption_template: str = "default",
        output_format: str = "vertical",
        add_subtitles: bool = True,
        webcam_box: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Render a single clip in the thread pool and return clip_info dict, or None on failure."""
        try:
            start_seconds = parse_timestamp_to_seconds(segment["start_time"])
            end_seconds = parse_timestamp_to_seconds(segment["end_time"])
            duration = end_seconds - start_seconds

            if duration <= 0:
                logger.warning(
                    f"Skipping clip {clip_index + 1}: invalid duration {duration:.1f}s"
                )
                return None

            clip_filename = (
                f"clip_{clip_index + 1}_"
                f"{segment['start_time'].replace(':', '')}-"
                f"{segment['end_time'].replace(':', '')}.mp4"
            )
            clip_path = output_dir / clip_filename

            success = await run_in_thread(
                create_optimized_clip,
                video_path,
                start_seconds,
                end_seconds,
                clip_path,
                add_subtitles,
                font_family,
                font_size,
                font_color,
                caption_template,
                output_format,
                webcam_box,
            )

            if not success:
                logger.error(f"Failed to create clip {clip_index + 1}")
                return None

            logger.info(f"Created clip {clip_index + 1}: {duration:.1f}s")
            return {
                "clip_id": clip_index + 1,
                "filename": clip_filename,
                "path": str(clip_path),
                "start_time": segment["start_time"],
                "end_time": segment["end_time"],
                "duration": duration,
                "text": segment.get("text", ""),
                "relevance_score": segment.get("relevance_score", 0.0),
                "reasoning": segment.get("reasoning", ""),
                "virality_score": segment.get("virality_score", 0),
                "hook_score": segment.get("hook_score", 0),
                "engagement_score": segment.get("engagement_score", 0),
                "value_score": segment.get("value_score", 0),
                "shareability_score": segment.get("shareability_score", 0),
                "hook_type": segment.get("hook_type"),
            }
        except Exception as e:
            logger.error(f"Error creating clip {clip_index + 1}: {e}")
            return None

    @staticmethod
    async def apply_single_transition(
        prev_clip_path: Path,
        current_clip_info: Dict[str, Any],
        clip_index: int,
        output_dir: Path,
    ) -> Dict[str, Any]:
        """Return the original clip info.

        Standalone exports intentionally do not depend on adjacent clips.
        """
        logger.info(
            "Skipping inter-clip transition for clip %s to preserve standalone exports",
            clip_index + 1,
        )
        return current_clip_info

    @staticmethod
    def determine_source_type(url: str) -> str:
        """Determine if source is YouTube or uploaded file."""
        video_id = get_youtube_video_id(url)
        return "youtube" if video_id else "video_url"

    @staticmethod
    async def process_video_complete(
        url: str,
        source_type: str,
        task_id: Optional[str] = None,
        font_family: str = "TikTokSans-Regular",
        font_size: int = 24,
        font_color: str = "#FFFFFF",
        caption_template: str = "default",
        processing_mode: str = "fast",
        output_format: str = "vertical",
        add_subtitles: bool = True,
        webcam_box: Optional[str] = None,
        quality: str = "high",
        cached_transcript: Optional[str] = None,
        cached_analysis_json: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str, str], Awaitable[None]]] = None,
        should_cancel: Optional[Callable[[], Awaitable[bool]]] = None,
    ) -> Dict[str, Any]:
        """
        Complete video processing pipeline supporting long videos and quality selection.
        """
        try:
            if should_cancel and await should_cancel():
                raise Exception("Task cancelled")

            # Step 1: Download video with quality selection
            if progress_callback:
                await progress_callback(5, "Downloading video...", "processing")

            if source_type == "youtube":
                video_path = await VideoService.download_video(url, task_id=task_id, quality=quality)
                if not video_path:
                    raise Exception("Failed to download video")
            else:
                video_path = VideoService.resolve_local_video_path(url)
                if not video_path.exists():
                    raise Exception("Video file not found")

            # Step 1.5: Auto-detect webcam region for gaming layout if not provided
            if output_format == "gaming" and not webcam_box:
                if progress_callback:
                    await progress_callback(7, "Detecting webcam region (GPU)...", "processing")
                
                try:
                    # Run robust multi-frame detection in a thread
                    detected_box = await run_in_thread(detect_webcam_region, video_path)
                    if detected_box:
                        webcam_box = detected_box
                        logger.info(f"Auto-detected webcam box: {webcam_box}")
                except Exception as e:
                    logger.warning(f"Auto-webcam detection failed: {e}")

            # Step 2: Split video into segments (90 mins each)
            segments = await VideoService.split_video_into_segments(video_path)
            num_segments = len(segments)
            logger.info(f"Processing video in {num_segments} parts")

            all_segments_json: List[Dict[str, Any]] = []
            combined_transcript = []
            summaries = []
            key_topics_combined = set()

            # Step 3: Loop through segments
            for i, (seg_path, start_offset, end_offset) in enumerate(segments):
                if should_cancel and await should_cancel():
                    raise Exception("Task cancelled")

                part_base_progress = 10 + (i / num_segments) * 80
                part_label = f" (Part {i+1}/{num_segments})" if num_segments > 1 else ""

                if progress_callback:
                    await progress_callback(int(part_base_progress), f"Generating transcript{part_label}...", "processing")

                # Transcription
                seg_transcript = await VideoService.generate_transcript(
                    seg_path, processing_mode=processing_mode
                )
                combined_transcript.append(seg_transcript)

                if progress_callback:
                    await progress_callback(int(part_base_progress + 5 / num_segments), f"Analyzing content{part_label}...", "processing")

                # AI Analysis
                seg_analysis = await VideoService.analyze_transcript(seg_transcript)
                if seg_analysis.summary:
                    summaries.append(seg_analysis.summary)
                if seg_analysis.key_topics:
                    key_topics_combined.update(seg_analysis.key_topics)

                # Collect segments and adjust timestamps
                for rel_seg in seg_analysis.most_relevant_segments:
                    # rel_seg can be a dict or object depending on implementation
                    s_time = rel_seg.get("start_time") if isinstance(rel_seg, dict) else rel_seg.start_time
                    e_time = rel_seg.get("end_time") if isinstance(rel_seg, dict) else rel_seg.end_time
                    text = rel_seg.get("text", "") if isinstance(rel_seg, dict) else rel_seg.text
                    score = rel_seg.get("relevance_score", 0.0) if isinstance(rel_seg, dict) else rel_seg.relevance_score
                    reason = rel_seg.get("reasoning", "") if isinstance(rel_seg, dict) else rel_seg.reasoning

                    abs_start = parse_timestamp_to_seconds(s_time) + start_offset
                    abs_end = parse_timestamp_to_seconds(e_time) + start_offset

                    def format_ts(s):
                        return f"{int(s//60):02d}:{int(s%60):02d}"

                    all_segments_json.append({
                        "start_time": format_ts(abs_start),
                        "end_time": format_ts(abs_end),
                        "text": text,
                        "relevance_score": score,
                        "reasoning": reason,
                        "part": i + 1
                    })

            # Fast mode clip limit
            if processing_mode == "fast":
                all_segments_json = all_segments_json[: config.fast_mode_max_clips]

            # Consolidate results
            final_transcript = "\n\n".join(combined_transcript)
            final_summary = " ".join(summaries)
            final_key_topics = list(key_topics_combined)

            if progress_callback:
                await progress_callback(95, "Finalizing analysis...", "processing")

            return {
                "segments": all_segments_json,
                "segments_to_render": all_segments_json,
                "video_path": str(video_path),
                "clips": [],
                "summary": final_summary,
                "key_topics": final_key_topics,
                "transcript": final_transcript,
                "analysis_json": json.dumps({
                    "summary": final_summary,
                    "key_topics": final_key_topics,
                    "most_relevant_segments": all_segments_json,
                }),
            }

        except Exception as e:
            logger.error(f"Error in video processing pipeline: {e}")
            raise
