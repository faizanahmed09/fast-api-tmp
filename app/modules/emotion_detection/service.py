"""
Emotion detection service using OpenSmile.
Extracts emotional attributes from audio (pitch, tone, energy).
"""
import logging
import tempfile
import os
from typing import Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class EmotionDetectionService:
    """Service for detecting emotion from audio using OpenSmile."""
    
    def __init__(self):
        """Initialize OpenSmile emotion detection service."""
        logger.info("=" * 60)
        logger.info("Initializing EmotionDetectionService...")
        try:
            import opensmile
            logger.info("OpenSmile library imported successfully")
            # Use ComParE feature set for faster processing
            # eGeMAPSv02 has 88 features, ComParE_2016 is optimized
            self.smile = opensmile.Smile(
                feature_set=opensmile.FeatureSet.eGeMAPSv02,
                feature_level=opensmile.FeatureLevel.Functionals,
                num_workers=2,  # Parallel processing
            )
            self.opensmile_available = True
            logger.info("✓ OpenSmile initialized successfully - REAL MODEL ACTIVE")
            logger.info(f"Feature set: eGeMAPSv02, Level: Functionals, Workers: 2")
        except ImportError as e:
            logger.warning("✗ OpenSmile not available, using mock emotion detection")
            logger.warning(f"Import error: {e}")
            self.smile = None
            self.opensmile_available = False
        except Exception as e:
            logger.error(f"✗ Failed to initialize OpenSmile: {e}")
            self.smile = None
            self.opensmile_available = False
        logger.info("=" * 60)
    
    async def detect_emotion(self, audio_data: bytes, filename: str = "audio.wav") -> Dict:
        """
        Detect emotion from audio data.
        
        Args:
            audio_data: Binary audio data
            filename: Original filename (for extension detection)
        
        Returns:
            Dictionary with 'emotion' and 'attributes' keys
        
        Raises:
            Exception: If emotion detection fails
        """
        logger.info(f"[DETECT_EMOTION] Starting emotion detection for file: {filename}")
        logger.info(f"[DETECT_EMOTION] Audio data size: {len(audio_data)} bytes")
        logger.info(f"[DETECT_EMOTION] OpenSmile available: {self.opensmile_available}")
        
        if self.smile is None:
            # Fallback to mock emotion detection
            logger.warning("⚠ OpenSmile not available, using MOCK detection (not real model)")
            return await self._mock_emotion_detection(audio_data)
        
        temp_path = None
        
        try:
            # Save audio to temporary file (OpenSmile supports MP3, WAV, etc.)
            suffix = Path(filename).suffix.lower() or ".wav"
            
            # Create temp file without automatic deletion (Windows compatibility)
            # Use buffered write for better performance
            temp_fd, temp_path = tempfile.mkstemp(suffix=suffix)
            try:
                # Write audio data in chunks for large files
                chunk_size = 8192
                for i in range(0, len(audio_data), chunk_size):
                    os.write(temp_fd, audio_data[i:i+chunk_size])
                os.close(temp_fd)
                
                # Verify file exists and is readable
                if not os.path.exists(temp_path):
                    raise FileNotFoundError(f"Temporary file not found: {temp_path}")
                
                file_size = os.path.getsize(temp_path)
                if file_size == 0:
                    raise ValueError(f"Temporary file is empty: {temp_path}")
                
                logger.info(f"[OPENSMILE] Processing audio file: {temp_path} (size: {file_size} bytes)")
                logger.info(f"[OPENSMILE] Calling OpenSmile.process_file() - REAL MODEL EXTRACTION")
                
                # Extract features using OpenSmile (supports MP3, WAV, FLAC, etc.)
                features = self.smile.process_file(temp_path)
                
                logger.info(f"[OPENSMILE] ✓ Feature extraction completed")
                logger.info(f"[OPENSMILE] Features shape: {features.shape if features is not None else 'None'}")
            except:
                # Close fd if still open
                try:
                    os.close(temp_fd)
                except:
                    pass
                raise
            
            if features is None or features.empty:
                raise ValueError("OpenSmile returned empty features")
            
            # Extract key emotional attributes
            logger.info(f"[PROCESSING] Extracting emotional attributes from OpenSmile features")
            attributes = self._extract_emotional_attributes(features)
            logger.info(f"[PROCESSING] Extracted attributes: {attributes}")
            
            # Classify emotion based on attributes
            logger.info(f"[CLASSIFICATION] Classifying emotion based on attributes")
            emotion = self._classify_emotion(attributes)
            logger.info(f"[CLASSIFICATION] ✓ Classified as: {emotion}")
            
            logger.info(f"Emotion detected: {emotion} (pitch: {attributes.get('pitch_mean', 0):.2f}, energy: {attributes.get('energy', 0):.2f}, rate: {attributes.get('speaking_rate', 0):.2f})")
            logger.debug(f"Full attributes: {attributes}")
            
            return {
                "emotion": emotion,
                "attributes": attributes,
            }
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Emotion detection error: {error_msg}", exc_info=True)
            
            # Check for missing dependencies
            if "mediainfo" in error_msg.lower():
                logger.error("Missing mediainfo dependency. Install with: choco install mediainfo (Windows) or apt-get install mediainfo (Linux)")
                raise Exception("MediaInfo is required for MP3 processing. Please install it: https://mediaarea.net/en/MediaInfo/Download/Windows")
            
            # Return neutral on other errors
            logger.warning("Returning neutral emotion due to processing error")
            return {
                "emotion": "neutral",
                "attributes": {
                    "pitch_mean": 0.5,
                    "energy": 0.5,
                    "speaking_rate": 0.5,
                },
            }
        
        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                    logger.debug(f"Cleaned up temp file: {temp_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_path}: {e}")
    
    def _extract_emotional_attributes(self, features) -> Dict[str, float]:
        """
        Extract normalized emotional attributes from OpenSmile features.
        
        Args:
            features: OpenSmile feature dataframe
        
        Returns:
            Dictionary of normalized attributes (0-1 range)
        """
        import numpy as np
        
        # Convert to dict and get first row (for functionals)
        feature_dict = features.iloc[0].to_dict()
        
        # Extract key features
        pitch_mean = feature_dict.get("F0semitoneFrom27.5Hz_sma3nz_amean", 0)
        energy_mean = feature_dict.get("loudness_sma3_amean", 0)
        speaking_rate = feature_dict.get("loudness_sma3_percentile20.0", 0)
        
        logger.debug(f"[FEATURES] Raw pitch: {pitch_mean}, energy: {energy_mean}, rate: {speaking_rate}")
        
        # Normalize to 0-1 range (rough estimates)
        attributes = {
            "pitch_mean": np.clip((pitch_mean + 100) / 200, 0, 1),
            "energy": np.clip((energy_mean + 40) / 80, 0, 1),
            "speaking_rate": np.clip((speaking_rate + 40) / 80, 0, 1),
        }
        
        return attributes
    
    def _classify_emotion(self, attributes: Dict[str, float]) -> str:
        """
        Classify emotion based on acoustic attributes.
        
        Args:
            attributes: Dictionary of normalized attributes
        
        Returns:
            Emotion label: happy, sad, angry, neutral, or surprised
        """
        pitch = attributes.get("pitch_mean", 0.5)
        energy = attributes.get("energy", 0.5)
        speaking_rate = attributes.get("speaking_rate", 0.5)
        
        # Rule-based classification with balanced thresholds
        # Each emotion has distinct acoustic patterns
        
        # ANGRY: High energy + high pitch + fast rate (shouting)
        if energy > 0.7 and pitch > 0.6:
            return "angry"
        
        # ANGRY: Very high energy alone (aggressive)
        if energy > 0.8:
            return "angry"
        
        # HAPPY: Moderate-high pitch + moderate-high energy + faster rate (excited, positive)
        if pitch > 0.55 and pitch < 0.75 and energy > 0.5 and energy < 0.75 and speaking_rate > 0.55:
            return "happy"
        
        # SURPRISED: Very high pitch with sudden change (shocked, startled)
        # High pitch but not sustained high energy
        if pitch > 0.75 and energy < 0.7:
            return "surprised"
        
        # SURPRISED: High pitch + moderate energy + slow/moderate rate (unexpected)
        if pitch > 0.7 and energy > 0.45 and energy < 0.65 and speaking_rate < 0.6:
            return "surprised"
        
        # SAD: Low pitch + low energy + slow rate (depressed, tired)
        if pitch < 0.4 and energy < 0.4:
            return "sad"
        
        # SAD: Low energy alone (lethargic)
        if energy < 0.3:
            return "sad"
        
        # NEUTRAL: Everything else (moderate values, no strong patterns)
        # This includes most normal speech patterns
        return "neutral"
    
    async def _mock_emotion_detection(self, audio_data: bytes) -> Dict:
        """
        Mock emotion detection when OpenSmile is not available.
        
        Args:
            audio_data: Binary audio data
        
        Returns:
            Mock emotion data
        """
        import hashlib
        
        # Use audio hash to generate consistent mock data
        audio_hash = hashlib.md5(audio_data).hexdigest()
        hash_val = int(audio_hash[:8], 16) / (16**8)
        
        emotions = ["happy", "sad", "angry", "neutral", "surprised"]
        emotion_idx = int(hash_val * len(emotions))
        emotion = emotions[emotion_idx]
        
        logger.warning(f"⚠ MOCK DETECTION USED (not real model): {emotion}")
        logger.warning(f"⚠ Install OpenSmile to use real emotion detection")
        
        return {
            "emotion": emotion,
            "attributes": {
                "pitch_mean": 0.5 + (hash_val - 0.5) * 0.3,
                "energy": 0.5 + (hash_val - 0.5) * 0.4,
                "speaking_rate": 0.5,
            },
        }


# Global service instance
emotion_detection_service = EmotionDetectionService()


