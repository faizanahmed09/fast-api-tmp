"""
Emotion detection service using OpenSmile.
Analyzes acoustic features (pitch, energy, voice quality) for emotion detection.
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
            
            # Classify emotion based on acoustic features
            logger.info(f"[CLASSIFICATION] Classifying emotion based on acoustic features")
            emotion = self._classify_emotion(attributes)
            logger.info(f"[CLASSIFICATION] ✓ Classified as: {emotion}")
            
            logger.info(f"✓ FINAL RESULT: {emotion.upper()}")
            logger.info(f"  Features: pitch={attributes.get('pitch_mean', 0):.2f}, pitch_var={attributes.get('pitch_std', 0):.2f}, loudness={attributes.get('loudness_mean', 0):.2f}, loudness_var={attributes.get('loudness_std', 0):.2f}")
            
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
        Extract comprehensive emotional attributes from OpenSmile eGeMAPSv02 features.
        Uses multiple acoustic features for accurate emotion detection.
        
        Args:
            features: OpenSmile feature dataframe
        
        """
        if features is None or features.empty:
            logger.warning("No features to extract")
            return {
                "pitch_mean": 0,
                "pitch_std": 0,
                "loudness_mean": 0,
                "loudness_std": 0,
            }
        
        # Get the first row (single audio file)
        feature_row = features.iloc[0]
        
        # === ONLY 4 CRITICAL FEATURES ===
        # 1. Pitch Mean - How high/low the voice is
        pitch_mean = feature_row.get("F0semitoneFrom27.5Hz_sma3nz_amean", 0)
        
        # 2. Pitch Variation - How expressive vs monotone
        pitch_std = feature_row.get("F0semitoneFrom27.5Hz_sma3nz_stddevNorm", 0)
        
        # 3. Loudness Mean - How loud the voice is
        loudness_mean = feature_row.get("loudness_sma3_amean", 0)
        
        # 4. Loudness Variation - How dynamic vs flat
        loudness_std = feature_row.get("loudness_sma3_stddevNorm", 0)
        
        logger.info("=" * 80)
        logger.info("[FEATURES] 4 CRITICAL VALUES:")
        logger.info(f"  1. Pitch Mean: {pitch_mean:.2f} semitones (high/low)")
        logger.info(f"  2. Pitch Variation: {pitch_std:.2f} (expressive/monotone)")
        logger.info(f"  3. Loudness Mean: {loudness_mean:.2f} dB (loud/quiet)")
        logger.info(f"  4. Loudness Variation: {loudness_std:.2f} (dynamic/flat)")
        logger.info("=" * 80)
        
        # Return only what we need
        return {
            "pitch_mean": float(pitch_mean),
            "pitch_std": float(pitch_std),
            "loudness_mean": float(loudness_mean),
            "loudness_std": float(loudness_std),
        }
    
    def _classify_emotion(self, attributes: Dict[str, float]) -> str:
        """
        Classify emotion using RELATIVE comparisons of OpenSmile features.
        Uses percentile-based analysis instead of absolute thresholds.
        
        Args:
            attributes: Dictionary of acoustic attributes from OpenSmile
        
        Returns:
            Emotion label: happy, sad, angry, or neutral
        """
        # Extract only the 4 critical features
        pitch_mean = attributes.get("pitch_mean", 0)
        pitch_std = attributes.get("pitch_std", 0)
        loudness_mean = attributes.get("loudness_mean", 0)
        loudness_std = attributes.get("loudness_std", 0)
        
        logger.info("=" * 80)
        logger.info("[CLASSIFY] EMOTION CLASSIFICATION ANALYSIS")
        logger.info(f"  Pitch Mean: {pitch_mean:.2f} semitones")
        logger.info(f"  Loudness Mean: {loudness_mean:.2f} dB")
        logger.info(f"  Loudness Std: {loudness_std:.2f}")
        logger.info(f"  Pitch Std: {pitch_std:.2f}")
        
        # Simple, direct scoring based on key features
        scores = {
            "neutral": 0,
            "happy": 0,
            "sad": 0,
            "angry": 0
        }
        
        # === HAPPY EMOTION (Check first - positive emotions) ===
        # Key indicators: MODERATE-HIGH PITCH + VARIATION + GOOD ENERGY.
        # High, lively voices (excited, laughing) should be happy, not angry.

        if 28.0 <= pitch_mean <= 36.0:
            # Strong happy: clearly expressive
            if pitch_std > 0.30:
                scores["happy"] += 6
                logger.info(
                    f"  [HAPPY] Pleasant/high pitch ({pitch_mean:.1f}) with strong variation ({pitch_std:.2f}) (+6)"
                )
            # Moderate happy: moderate variation + good energy
            elif pitch_std > 0.22 and 0.8 <= loudness_mean <= 1.3 and 0.85 <= loudness_std <= 1.3:
                scores["happy"] += 5
                logger.info(
                    f"  [HAPPY] Pleasant/high pitch ({pitch_mean:.1f}) with moderate variation ({pitch_std:.2f}) and good energy ({loudness_mean:.1f} dB, var {loudness_std:.2f}) (+5)"
                )
            # Excited happy: high pitch + clearly high energy, even if variation is moderate
            elif pitch_mean >= 30.0 and loudness_mean >= 1.0 and loudness_std >= 0.75:
                scores["happy"] += 4
                logger.info(
                    f"  [HAPPY] Excited voice: high pitch ({pitch_mean:.1f}), loud ({loudness_mean:.1f} dB), dynamic ({loudness_std:.2f}) (+4)"
                )
        
        # === ANGRY EMOTION ===
        # Key indicators: EXTREMELY HIGH PITCH + VERY LOUD + STRONG DYNAMICS (tense/shouting)
        if pitch_mean > 37:  # Very, very high pitch (shouting)
            scores["angry"] += 5
            logger.info(f"  [ANGRY] Extremely high pitch ({pitch_mean:.1f}) - shouting/yelling (+5)")
        elif pitch_mean > 35:  # High pitch
            scores["angry"] += 3
            logger.info(f"  [ANGRY] Very high pitch ({pitch_mean:.1f}) - raised/tense voice (+3)")
        
        if loudness_mean > 1.4:  # Very loud (shouting)
            scores["angry"] += 4
            logger.info(f"  [ANGRY] Very loud ({loudness_mean:.1f} dB) - shouting (+4)")
        elif loudness_mean > 1.2:  # Loud
            scores["angry"] += 2
            logger.info(f"  [ANGRY] Loud ({loudness_mean:.1f} dB) (+2)")
        
        if loudness_std > 1.1:  # Strong energy variation (agitated)
            scores["angry"] += 2
            logger.info(f"  [ANGRY] High energy variation ({loudness_std:.1f}) - agitated (+2)")
        
        # Low pitch variation indicates tension (angry), not happiness
        if pitch_std < 0.2 and pitch_mean > 30:  # Tense/monotone at high pitch
            scores["angry"] += 2
            logger.info(f"  [ANGRY] Tense voice (low variation {pitch_std:.2f} at high pitch) (+2)")
        
        # === SAD EMOTION ===
        # Key indicators: CLEAR LOW PITCH + CLEARLY LOW ENERGY
        # We want most everyday speech to be NEUTRAL. SAD should only fire
        # when both pitch AND energy are clearly low.
        if pitch_mean < 25:  # Very low pitch
            scores["sad"] += 4
            logger.info(f"  [SAD] Very low pitch ({pitch_mean:.1f}) - depressed tone (+4)")

        if pitch_std < 0.18:  # Strongly monotone
            scores["sad"] += 3
            logger.info(f"  [SAD] Very low pitch variation ({pitch_std:.2f}) - flat/monotone (+3)")

        if loudness_mean < 0.4:  # Clearly quiet / low energy
            scores["sad"] += 4
            logger.info(f"  [SAD] Very low energy ({loudness_mean:.1f} dB) (+4)")

        if loudness_std < 0.7:  # Very flat dynamics
            scores["sad"] += 2
            logger.info(f"  [SAD] Very flat energy dynamics ({loudness_std:.1f}) (+2)")

        # === NEUTRAL (Default) ===
        # Everything else that doesn't match strong patterns
        if 26 <= pitch_mean <= 32:  # Normal-ish pitch range
            scores["neutral"] += 2
            logger.info(f"  [NEUTRAL] Normal pitch range ({pitch_mean:.1f}) (+2)")

        if 0.3 <= loudness_mean <= 1.0:  # Normal loudness
            scores["neutral"] += 2
            logger.info(f"  [NEUTRAL] Normal loudness ({loudness_mean:.1f} dB) (+2)")

        # Determine final emotion
        max_score = max(scores.values())

        logger.info(f"\n[CLASSIFY] FINAL SCORES:")
        for emotion, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {emotion.upper()}: {score}")

        # Get emotion with highest score (default to neutral if all zeros)
        if max_score == 0:
            detected_emotion = "neutral"
            logger.info(f"\n[CLASSIFY] ✓ RESULT: NEUTRAL (no clear indicators)")
        else:
            detected_emotion = max(scores, key=scores.get)

        # If SAD wins but looks borderline (small SAD advantage, not clearly low energy),
        # prefer NEUTRAL so we don't over-detect sadness for everyday neutral speech.
        sad_score = scores["sad"]
        neutral_score = scores["neutral"]
        if (
            detected_emotion == "sad"
            and sad_score <= 5  # only small/medium SAD evidence
            and (sad_score - neutral_score) <= 3
            and 24.5 <= pitch_mean <= 28.5
            and 0.35 <= loudness_mean <= 0.9
            and 0.7 <= loudness_std <= 1.1  # not extremely flat or extreme
        ):
            detected_emotion = "neutral"
            logger.info("  [NEUTRAL_OVERRIDE] Borderline low-pitch, low-energy speech treated as NEUTRAL instead of SAD")

        if detected_emotion == "neutral" and max_score != 0:
            logger.info(f"\n[CLASSIFY] ✓ RESULT: NEUTRAL (tie-broken from scores)")
        else:
            logger.info(f"\n[CLASSIFY] ✓ RESULT: {detected_emotion.upper()} (score: {max_score})")

        logger.info("=" * 80)
        return detected_emotion
    
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


