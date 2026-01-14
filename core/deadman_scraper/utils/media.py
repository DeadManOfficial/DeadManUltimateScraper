"""
Media Laundering Module
=======================
NASA Standard: Robust scrubbing of visual and acoustic watermarks.
Integrates FFmpeg for high-fidelity signal degradation and inpainting.
"""

import logging
import random
import subprocess
from pathlib import Path

logger = logging.getLogger("MediaLaunderer")

class MediaLaunderer:
    """
    Cleans media files by removing SynthID and other watermarking signatures.
    """

    @staticmethod
    def check_ffmpeg() -> bool:
        """Verify ffmpeg is installed and available."""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("FFmpeg not found in PATH.")
            return False

    @staticmethod
    def clean_audio(input_path: Path, output_path: Path | None = None) -> Path | None:
        """
        Scrub audio watermarks via signal jitter and pink noise injection.
        """
        if not output_path:
            output_path = input_path.parent / f"{input_path.stem}_cleaned{input_path.suffix}"

        logger.info(f"Scrubbing audio: {input_path}")

        # Jitter + Noise + Re-encoding logic from launderer.py
        jitter = 1.0 + (random.randint(1, 3) / 100.0)

        cmd = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-filter_complex",
            f"atempo={jitter},volume=1.0[main];anoisesrc=c=pink:r=44100:a=0.001[noise];[main][noise]amix=inputs=2:duration=shortest",
            "-c:a", "libmp3lame", "-q:a", "2",
            str(output_path)
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            logger.info(f"Cleaned audio saved: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to clean audio {input_path}: {e}")
            return None

    @staticmethod
    def clean_video(input_path: Path, output_path: Path | None = None) -> Path | None:
        """
        Remove visual watermarks using Smart Interpolation (Delogo).
        """
        if not output_path:
            output_path = input_path.parent / f"{input_path.stem}_inpainted{input_path.suffix}"

        logger.info(f"Inpainting video: {input_path}")

        jitter = 1.02
        cmd = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-filter_complex",
            f"[0:v]delogo=x=0:y=h-100:w=w:h=100:show=0[video_clean];[0:a]atempo={jitter},volume=1.0[audio_clean]",
            "-map", "[video_clean]", "-map", "[audio_clean]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            str(output_path)
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            logger.info(f"Inpainted video saved: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to inpaint video {input_path}: {e}")
            return None
