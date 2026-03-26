import asyncio
import logging
from pathlib import Path
from src.video_utils import get_video_transcript

logging.basicConfig(level=logging.INFO)

async def test():
    # We will use the jfk.wav wrapped as a "video" to test the flow
    sample_video = Path("/home/devjo/supoclip/whisper.cpp/samples/jfk.wav")
    print(f"Testing transcription for {sample_video}...")
    
    transcript = get_video_transcript(sample_video, "best")
    print("\n--- FORMATTED TRANSCRIPT ---")
    print(transcript)
    print("----------------------------\n")
    
    # Check cache
    cache_path = sample_video.with_suffix(".transcript_cache.json")
    if cache_path.exists():
        print(f"Cache file {cache_path} successfully written!")
        import json
        with open(cache_path, "r") as f:
            data = json.load(f)
            print(f"Cache has {len(data['words'])} words and {len(data['utterances'])} utterances.")
            
if __name__ == "__main__":
    asyncio.run(test())
