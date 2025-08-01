import os
from typing import Any

from fastapi import Path

from app.utils.logging_config import get_logger

"""
Multimedia parsers for audio and video files
Supports transcription and metadata extraction
"""

from pathlib import Path

# Audio/Video processing libraries
try:
    import whisper

    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

try:
    import moviepy.editor as mp
    from moviepy.video.tools.subtitles import SubtitlesClip

    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False

try:
    from pydub import AudioSegment
    from pydub.utils import mediainfo

    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

try:
    import speech_recognition as sr

    HAS_SPEECH_RECOGNITION = True
except ImportError:
    HAS_SPEECH_RECOGNITION = False

from app.ingestion.engine import FileParser
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AudioParser(FileParser):
    """Parser for audio files with transcription support"""

    SUPPORTED_TYPES = {
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/ogg",
        "audio/flac",
        "audio/x-flac",
        "audio/m4a",
        "audio/x-m4a",
        "audio/mp4",
    }

    def __init__(self):
        self.transcriber = None
        if HAS_WHISPER:
            # Use tiny model by default for speed, can be configured
            model_name = os.environ.get("WHISPER_MODEL", "tiny")
            try:
                self.transcriber = whisper.load_model(model_name)
                logger.info(f"Loaded Whisper model: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to load Whisper model: {e}")
        elif HAS_SPEECH_RECOGNITION:
            self.transcriber = sr.Recognizer()
            logger.info("Using speech_recognition for audio transcription")
        else:
            logger.warning(
                "No audio transcription libraries available. "
                "Install with: pip install openai-whisper OR pip install SpeechRecognition"
            )

    async def parse(self, file_path: Path) -> dict[str, Any]:
        """Parse audio file and extract transcript and metadata"""
        metadata = {
            "format": "audio",
            "duration": 0,
            "sample_rate": None,
            "channels": None,
            "bitrate": None,
            "codec": None,
        }

        # Extract audio metadata
        if HAS_PYDUB:
            try:
                info = mediainfo(str(file_path))
                metadata.update(
                    {
                        "duration": float(info.get("duration", 0)),
                        "sample_rate": info.get("sample_rate"),
                        "channels": info.get("channels"),
                        "bitrate": info.get("bit_rate"),
                        "codec": info.get("codec_name"),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to extract audio metadata: {e}")

        # Transcribe audio
        transcript = ""
        if self.transcriber:
            try:
                if HAS_WHISPER and isinstance(self.transcriber, type(whisper.load_model("tiny"))):
                    # Use Whisper
                    result = self.transcriber.transcribe(str(file_path))
                    transcript = result["text"]

                    # Add segments with timestamps if available
                    if "segments" in result:
                        segments = []
                        for seg in result["segments"]:
                            segments.append(
                                {
                                    "start": seg["start"],
                                    "end": seg["end"],
                                    "text": seg["text"].strip(),
                                }
                            )
                        metadata["segments"] = segments

                elif HAS_SPEECH_RECOGNITION:
                    # Use speech_recognition
                    with sr.AudioFile(str(file_path)) as source:
                        audio = self.transcriber.record(source)
                        transcript = self.transcriber.recognize_google(audio)

            except Exception as e:
                logger.error(f"Failed to transcribe audio: {e}")
                transcript = f"[Transcription failed: {str(e)}]"
        else:
            transcript = (
                "[Audio transcription not available - install whisper or speech_recognition]"
            )

        return {"content": transcript, "metadata": metadata}

    def supports(self, mime_type: str) -> bool:
        return mime_type in self.SUPPORTED_TYPES


class VideoParser(FileParser):
    """Parser for video files with frame extraction and transcription"""

    SUPPORTED_TYPES = {
        "video/mp4",
        "video/x-msvideo",
        "video/avi",
        "video/quicktime",
        "video/x-matroska",  # Matroska/MKV container
        "video/webm",
        "video/mpeg",
        "video/ogg",
    }

    # File extensions for fallback detection
    SUPPORTED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".mpg", ".mpeg", ".ogv"}

    def __init__(self):
        if not HAS_MOVIEPY:
            logger.warning(
                "MoviePy not installed. Video parsing will be limited. "
                "Install with: pip install moviepy"
            )

        # Initialize audio parser for video audio extraction
        self.audio_parser = AudioParser() if (HAS_WHISPER or HAS_SPEECH_RECOGNITION) else None

    async def parse(self, file_path: Path) -> dict[str, Any]:
        """Parse video file and extract transcript, frames, and metadata"""
        metadata = {
            "format": "video",
            "duration": 0,
            "fps": None,
            "resolution": None,
            "codec": None,
            "has_audio": False,
        }

        content_parts = []

        if HAS_MOVIEPY:
            try:
                logger.info(f"Processing video file: {file_path.name} ({file_path.suffix.lower()})")
                video = mp.VideoFileClip(str(file_path))

                # Extract metadata
                metadata.update(
                    {
                        "duration": video.duration,
                        "fps": video.fps,
                        "resolution": f"{video.w}x{video.h}",
                        "has_audio": video.audio is not None,
                        "container": (
                            "mkv"
                            if file_path.suffix.lower() == ".mkv"
                            else file_path.suffix.lower()[1:]
                        ),
                    }
                )

                # Extract audio and transcribe if available
                if video.audio and self.audio_parser:
                    try:
                        # Export audio to temporary file
                        import tempfile

                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
                            video.audio.write_audiofile(tmp_audio.name, logger=None)

                            # Transcribe audio
                            audio_result = await self.audio_parser.parse(Path(tmp_audio.name))
                            if audio_result["content"]:
                                content_parts.append(
                                    f"[Audio Transcript]\n{audio_result['content']}"
                                )

                                # Include segment data if available
                                if "segments" in audio_result["metadata"]:
                                    metadata["audio_segments"] = audio_result["metadata"][
                                        "segments"
                                    ]

                            # Clean up temp file
                            os.unlink(tmp_audio.name)
                    except Exception as e:
                        logger.warning(f"Failed to extract audio from video: {e}")

                # Extract key frames description (placeholder for future CV integration)
                content_parts.append(
                    f"\n[Video Info]\nDuration: {metadata['duration']:.2f} seconds"
                )
                content_parts.append(f"Resolution: {metadata['resolution']}")
                content_parts.append(f"FPS: {metadata['fps']}")

                # Close video file
                video.close()

            except Exception as e:
                logger.error(f"Failed to parse video with MoviePy: {e}")
                content_parts.append(f"[Video parsing failed: {str(e)}]")
        else:
            content_parts.append("[Video parsing not available - install moviepy]")

        return {"content": "\n\n".join(content_parts), "metadata": metadata}

    def supports(self, mime_type: str, file_path: Path | None = None) -> bool:
        """Check if this parser supports the given MIME type or file extension"""
        # Primary check: MIME type
        if mime_type in self.SUPPORTED_TYPES:
            return True

        # Fallback: check file extension for cases where MIME detection fails
        if file_path and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
            logger.info(f"Supporting {file_path.suffix} file via extension fallback")
            return True

        return False


class SubtitleParser(FileParser):
    """Parser for subtitle files (SRT, VTT, etc.)"""

    SUPPORTED_TYPES = {
        "application/x-subrip",
        "text/vtt",
        "text/plain",  # Sometimes SRT files are detected as plain text
    }

    SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".sub", ".ass", ".ssa"}

    async def parse(self, file_path: Path) -> dict[str, Any]:
        """Parse subtitle file and extract text with timestamps"""
        content_parts = []
        metadata = {
            "format": "subtitle",
            "subtitle_format": file_path.suffix.lower(),
            "segments": [],
        }

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            if file_path.suffix.lower() == ".srt":
                # Parse SRT format
                import re

                srt_pattern = re.compile(
                    r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)",
                    re.DOTALL,
                )

                for match in srt_pattern.finditer(content):
                    index, start_time, end_time, text = match.groups()
                    clean_text = text.strip().replace("\n", " ")
                    content_parts.append(clean_text)

                    metadata["segments"].append(
                        {
                            "index": int(index),
                            "start": start_time,
                            "end": end_time,
                            "text": clean_text,
                        }
                    )

            elif file_path.suffix.lower() == ".vtt":
                # Parse WebVTT format
                lines = content.split("\n")
                in_cue = False
                current_text = []

                for line in lines:
                    if "-->" in line:
                        in_cue = True
                    elif in_cue and line.strip() == "":
                        if current_text:
                            content_parts.append(" ".join(current_text))
                            current_text = []
                        in_cue = False
                    elif in_cue and line.strip():
                        current_text.append(line.strip())
            else:
                # Fallback: just extract all text
                content_parts = [content]

        except Exception as e:
            logger.error(f"Failed to parse subtitle file: {e}")
            content_parts = [f"[Subtitle parsing failed: {str(e)}]"]

        return {"content": "\n".join(content_parts), "metadata": metadata}

    def supports(self, mime_type: str) -> bool:
        # Check both mime type
        return mime_type in self.SUPPORTED_TYPES
