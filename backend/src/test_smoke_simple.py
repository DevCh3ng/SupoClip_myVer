import sys
import os
import asyncio
import random
import logging
from pathlib import Path

# Add parent directory to sys.path so 'src' can be found
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(current_dir))

try:
    from src.services.video_service import VideoService
    from src.video_utils import create_optimized_clip, VideoFileClip
except ImportError as e:
    print(f"Import Error: {e}")
    print("Please make sure you are running this from the backend or supoclip directory.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)

async def smoke_test(url: str, quality: str = "medium", transcribe: bool = True):
    video_service = VideoService()
    
    print(f"\n{'='*40}")
    print(f"   SUPOCLIP FULL SMOKE TEST")
    print(f"{'='*40}")
    print(f"URL: {url}")
    print(f"Quality: {quality}")
    print(f"Transcribe: {transcribe}")
    
    # 1. Download
    print("\n[1/4] Downloading video...")
    video_path = await video_service.download_video(url, quality=quality)
    if not video_path:
        print("Error: Download failed.")
        return
    print(f"Downloaded to: {video_path}")
    
    # 2. Transcribe (New)
    if transcribe:
        print("\n[2/4] Transcribing video (using Whisper base.en)...")
        from src.video_utils import get_video_transcript
        from src.utils.async_helpers import run_in_thread
        try:
            # This also caches the data for subtitle generation
            await run_in_thread(get_video_transcript, video_path)
            print("Transcription success (cached).")
        except Exception as e:
            print(f"Transcription failed: {e}")
            print("Proceeding without subtitles...")
    else:
        print("\n[2/4] Skipping transcription.")

    # 3. Pick random 30s
    print("\n[3/4] Analyzing duration...")
    try:
        video = VideoFileClip(str(video_path))
        duration = video.duration
        video.close()
    except Exception as e:
        print(f"Error reading video duration: {e}")
        return
    
    if duration < 30:
        start, end = 0, duration
    else:
        # Avoid the very end of the video
        safe_duration = max(0, duration - 35)
        start = random.uniform(0, safe_duration)
        end = start + 30
    
    print(f"Full duration: {duration:.1f}s")
    print(f"Selected range: {start:.1f}s - {end:.1f}s")
    
    # 4. Render
    print("\n[4/4] Rendering 30s clip (H.264, trying subtitles)...")
    output_path = Path("smoke_test_result.mp4")
    
    # We call the blocking function directly for this simple test
    # If transcribe=True, it will use the cached transcript from step 2
    success = create_optimized_clip(
        video_path=video_path,
        start_time=start,
        end_time=end,
        output_path=output_path,
        add_subtitles=True,
        output_format="original"
    )
    
    if success:
        print(f"\n{'*'*40}")
        print(f"SUCCESS! Smoke test complete.")
        print(f"Output file: {output_path.absolute()}")
        print(f"{'*'*40}\n")
    else:
        print("\nFAILURE: Clip rendering failed.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python src/test_smoke_simple.py <youtube_url> [quality] [transcribe:true/false]")
        print("Qualities: low, medium, high")
        sys.exit(1)
        
    url = sys.argv[1]
    quality = sys.argv[2] if len(sys.argv) > 2 else "medium"
    transcribe_str = sys.argv[3].lower() if len(sys.argv) > 3 else "true"
    transcribe = transcribe_str == "true"
    
    try:
        asyncio.run(smoke_test(url, quality, transcribe))
    except KeyboardInterrupt:
        print("\nAborted by user.")
