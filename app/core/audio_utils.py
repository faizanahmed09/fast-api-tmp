"""
Audio utility functions for format conversion and validation.
"""
import io
import logging
import subprocess
import tempfile
import os

logger = logging.getLogger(__name__)


def convert_to_wav(audio_data: bytes, source_format: str = "webm") -> bytes:
    """
    Convert audio data to WAV format for Deepgram compatibility using ffmpeg.
    
    Args:
        audio_data: Binary audio data in any format
        source_format: Source audio format (webm, mp3, m4a, etc.)
    
    Returns:
        WAV format audio data as bytes
    
    Raises:
        Exception: If conversion fails
    """
    try:
        # Detect format from common MIME types
        format_map = {
            "audio/webm": "webm",
            "audio/mp3": "mp3",
            "audio/mpeg": "mp3",
            "audio/m4a": "m4a",
            "audio/mp4": "mp4",
            "audio/wav": "wav",
            "audio/wave": "wav",
            "audio/flac": "flac",
            "audio/ogg": "ogg",
        }
        
        # Use provided source format or default to webm
        if source_format.startswith("audio/"):
            source_format = format_map.get(source_format, "webm")
        
        logger.info(f"[AUDIO_CONVERT] Converting {source_format} to WAV")
        
        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(suffix=f".{source_format}", delete=False) as input_file:
            input_path = input_file.name
            input_file.write(audio_data)
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as output_file:
            output_path = output_file.name
        
        try:
            # Use ffmpeg to convert to WAV with optimal settings for speech recognition
            # 16kHz sample rate, mono channel, 16-bit PCM
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-ar", "16000",  # Sample rate: 16kHz
                "-ac", "1",      # Channels: mono
                "-sample_fmt", "s16",  # Sample format: 16-bit signed integer
                "-f", "wav",     # Output format: WAV
                "-y",            # Overwrite output file
                output_path
            ]
            
            # Run ffmpeg
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            
            # Read converted WAV data
            with open(output_path, "rb") as f:
                wav_data = f.read()
            
            original_size_mb = len(audio_data) / (1024 * 1024)
            converted_size_mb = len(wav_data) / (1024 * 1024)
            
            logger.info(f"[AUDIO_CONVERT] Conversion successful")
            logger.info(f"[AUDIO_CONVERT] Original: {original_size_mb:.2f}MB → WAV: {converted_size_mb:.2f}MB")
            logger.info(f"[AUDIO_CONVERT] Settings: 16kHz, mono, 16-bit PCM")
            
            return wav_data
            
        finally:
            # Clean up temporary files
            try:
                os.unlink(input_path)
                os.unlink(output_path)
            except:
                pass
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        logger.error(f"[AUDIO_CONVERT] FFmpeg conversion failed: {error_msg}")
        raise Exception(f"Audio format conversion failed: {error_msg}")
    except Exception as e:
        logger.error(f"[AUDIO_CONVERT] Conversion failed: {str(e)}")
        raise Exception(f"Audio format conversion failed: {str(e)}")


def get_audio_info(audio_data: bytes, source_format: str = "webm") -> dict:
    """
    Get information about audio data using ffprobe.
    
    Args:
        audio_data: Binary audio data
        source_format: Source audio format
    
    Returns:
        Dictionary with audio information (duration, channels, sample_rate, etc.)
    """
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix=f".{source_format}", delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(audio_data)
        
        try:
            # Use ffprobe to get audio info
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                temp_path
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            
            import json
            info = json.loads(result.stdout.decode())
            
            # Extract relevant information
            format_info = info.get("format", {})
            stream_info = info.get("streams", [{}])[0]
            
            return {
                "duration_seconds": float(format_info.get("duration", 0)),
                "channels": int(stream_info.get("channels", 0)),
                "sample_rate": int(stream_info.get("sample_rate", 0)),
                "size_bytes": len(audio_data),
            }
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Failed to get audio info: {str(e)}")
        return {}
