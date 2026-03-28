"""
dump_transcript.py — Transcribe a video and write word-level timestamps to a .txt file.

Usage (inside the worker container):
    .venv/bin/python src/dump_transcript.py <video_path_or_youtube_url> [output.txt]

Examples:
    .venv/bin/python src/dump_transcript.py /app/uploads/Udc2U7IcbT4.mp4
    .venv/bin/python src/dump_transcript.py /app/uploads/Udc2U7IcbT4.mp4 words.txt
    .venv/bin/python src/dump_transcript.py "https://youtube.com/watch?v=..." words.txt
"""

import sys
import os
import asyncio
import json
import logging
from pathlib import Path

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(current_dir))

try:
    from src.video_utils import get_video_transcript
    from src.services.video_service import VideoService
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.WARNING)  # suppress info spam


def fmt_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS.mmm"""
    ms = int((seconds % 1) * 1000)
    s = int(seconds) % 60
    m = (int(seconds) // 60) % 60
    h = int(seconds) // 3600
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


async def main(source: str, output_path: str):
    video_path: Path | None = None

    # If source is a URL, download it first
    if source.startswith("http"):
        print(f"Downloading: {source}")
        svc = VideoService()
        video_path = await svc.download_video(source, quality="medium")
        if not video_path:
            print("Download failed.")
            sys.exit(1)
        print(f"Downloaded to: {video_path}")
    else:
        video_path = Path(source)
        if not video_path.exists():
            print(f"File not found: {video_path}")
            sys.exit(1)

    # Check if transcript is already cached
    cache_file = video_path.with_suffix(".transcript_cache.json")
    if cache_file.exists():
        print(f"Using cached transcript: {cache_file}")
    else:
        print("Transcribing (this may take a while)...")
        get_video_transcript(video_path)  # also caches

    # Load the raw cache (word-level data)
    if not cache_file.exists():
        print("Error: transcript cache not found after transcription.")
        sys.exit(1)

    with open(cache_file) as f:
        data = json.load(f)

    words = data.get("words", [])
    utterances = data.get("utterances", [])

    lines = []
    lines.append(f"=== TRANSCRIPT: {video_path.name} ===\n")
    lines.append(f"Total words: {len(words)}\n\n")

    if utterances:
        lines.append("--- SEGMENTS ---\n")
        for u in utterances:
            t_start = fmt_time(u.get("start", 0) / 1000 if u.get("start", 0) > 1000 else u.get("start", 0))
            t_end   = fmt_time(u.get("end", 0) / 1000 if u.get("end", 0) > 1000 else u.get("end", 0))
            lines.append(f"[{t_start} --> {t_end}]  {u.get('text', '')}\n")

        lines.append("\n--- WORD-LEVEL ---\n")

    for w in words:
        start = w.get("start", 0)
        end   = w.get("end", 0)
        # whisper.cpp stores in seconds already; AssemblyAI in ms — detect automatically
        if start > 1000:
            start /= 1000
            end   /= 1000
        text = w.get("text", "")
        conf = w.get("confidence", w.get("p", 1.0))
        lines.append(f"[{fmt_time(start)} --> {fmt_time(end)}]  {text}  (conf: {conf:.2f})\n")

    out = Path(output_path)
    out.write_text("".join(lines), encoding="utf-8")
    print(f"\nDone! Written to: {out.absolute()}")
    print(f"  {len(utterances)} segments, {len(words)} words")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    source = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else "transcript_dump.txt"
    asyncio.run(main(source, output))
