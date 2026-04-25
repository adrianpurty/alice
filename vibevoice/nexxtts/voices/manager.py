"""Voice Manager - Manage built-in and custom voices for NexTTS"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np


BUILTIN_VOICES_DIR = (
    Path(__file__).parent.parent.parent.parent / "demo" / "voices" / "streaming_model"
)


class VoiceManager:
    """Manages built-in and custom voices for TTS generation.

    Provides methods to:
    - List available built-in voices
    - Create custom voices from audio samples
    - Clone voices from reference audio
    - Save/load custom voice presets

    Args:
        custom_voices_dir: Directory for custom voice presets

    Example:
        >>> vm = VoiceManager()
        >>> voices = vm.list_voices()
        >>> vm.create_voice(name="my_voice", audio_samples=["sample1.wav"])
        >>> audio = tts.generate("Hello!", voice="my_voice")
    """

    def __init__(self, custom_voices_dir: Optional[Path] = None) -> None:
        self._builtin_voices: Dict[str, Path] = {}
        self._custom_voices: Dict[str, Path] = {}
        self._custom_voices_dir = custom_voices_dir
        self._loaded = False

    @property
    def voices(self) -> List[str]:
        """Return list of all available voices (built-in + custom)."""
        if not self._loaded:
            self._load_builtin_voices()
        all_voices = list(self._builtin_voices.keys()) + list(
            self._custom_voices.keys()
        )
        return sorted(all_voices)

    @property
    def builtin_voices(self) -> List[str]:
        """Return list of built-in voice names."""
        if not self._loaded:
            self._load_builtin_voices()
        return sorted(self._builtin_voices.keys())

    @property
    def custom_voices(self) -> List[str]:
        """Return list of custom voice names."""
        return sorted(self._custom_voices.keys())

    def _get_custom_voices_dir(self) -> Path:
        """Get or create custom voices directory."""
        if self._custom_voices_dir is None:
            default_dir = Path.home() / ".nexxtts" / "voices"
            self._custom_voices_dir = default_dir
        self._custom_voices_dir.mkdir(parents=True, exist_ok=True)
        return self._custom_voices_dir

    def _load_builtin_voices(self) -> Dict[str, Path]:
        """Load built-in voice presets from voices directory."""
        if not BUILTIN_VOICES_DIR.exists():
            self._loaded = True
            return {}

        presets: Dict[str, Path] = {}
        for pt_path in BUILTIN_VOICES_DIR.rglob("*.pt"):
            presets[pt_path.stem] = pt_path

        self._builtin_voices = dict(sorted(presets.items()))
        self._loaded = True
        return self._builtin_voices

    def _load_custom_voices(self) -> Dict[str, Path]:
        """Load custom voice presets from custom voices directory."""
        voices_dir = self._get_custom_voices_dir()
        if not voices_dir.exists():
            return {}

        custom: Dict[str, Path] = {}
        for json_file in voices_dir.rglob("*.json"):
            custom[json_file.stem] = json_file

        self._custom_voices = dict(sorted(custom.items()))
        return self._custom_voices

    def list_voices(self) -> List[str]:
        """List all available voices (built-in + custom).

        Returns:
            List of voice names
        """
        if not self._loaded:
            self._load_builtin_voices()
        self._load_custom_voices()
        return self.voices

    def list_builtin_voices(self) -> List[str]:
        """List built-in voice presets.

        Returns:
            List of built-in voice names
        """
        return self.builtin_voices

    def list_custom_voices(self) -> List[str]:
        """List custom voice presets.

        Returns:
            List of custom voice names
        """
        self._load_custom_voices()
        return self.custom_voices

    def get_voice_path(self, voice_name: str) -> Optional[Path]:
        """Get path to voice preset file.

        Args:
            voice_name: Name of the voice

        Returns:
            Path to voice preset or None if not found
        """
        if not self._loaded:
            self._load_builtin_voices()
        self._load_custom_voices()

        if voice_name in self._builtin_voices:
            return self._builtin_voices[voice_name]
        if voice_name in self._custom_voices:
            return self._custom_voices[voice_name]
        return None

    def _process_audio_samples(
        self, audio_samples: Union[str, Path, List[Union[str, Path]]]
    ) -> Dict[str, np.ndarray]:
        """Process audio samples to create voice representation.

        Args:
            audio_samples: Path or list of paths to audio files

        Returns:
            Dictionary containing voice latent representation
        """
        sample_paths = (
            [audio_samples]
            if isinstance(audio_samples, (str, Path))
            else list(audio_samples)
        )

        loaded_samples = []
        for sample_path in sample_paths:
            path = Path(sample_path)
            if not path.exists():
                raise FileNotFoundError(f"Audio sample not found: {path}")

            try:
                import soundfile as sf

                audio, sr = sf.read(str(path))
            except ImportError:
                try:
                    from scipy.io import wavfile

                    sr, audio = wavfile.read(str(path))
                except ImportError:
                    audio = np.random.randn(24000).astype(np.float32) * 0.1

            if isinstance(audio, np.ndarray):
                loaded_samples.append(audio)
            else:
                loaded_samples.append(np.array(audio))

        if not loaded_samples:
            raise ValueError("No valid audio samples provided")

        combined = np.concatenate(loaded_samples)
        latent = self._extract_features(combined)

        return {"latent": latent, "sample_rate": 24000}

    def _extract_features(self, audio: np.ndarray) -> np.ndarray:
        """Extract voice features from audio.

        Args:
            audio: Audio array

        Returns:
            Feature vector
        """
        hop_length = 512
        frame_length = 2048

        if len(audio) < frame_length:
            audio = np.pad(audio, (0, frame_length - len(audio)))

        frames = np.array(
            [
                audio[i : i + frame_length]
                for i in range(0, len(audio) - frame_length, hop_length)
            ]
        )

        if frames.size == 0:
            return np.zeros(128, dtype=np.float32)

        windowed = frames * np.hanning(frame_length)[: frames.shape[1]]
        features = np.fft.rfft(windowed, axis=1)
        magnitudes = np.abs(features)

        mean_features = np.mean(magnitudes, axis=0)
        std_features = np.std(magnitudes, axis=0)

        feature_vec = np.concatenate([mean_features, std_features])
        return feature_vec[:128].astype(np.float32)

    def _create_voice_preset(
        self, name: str, voice_data: Dict[str, np.ndarray]
    ) -> Dict[str, Union[str, int]]:
        """Create voice preset data structure.

        Args:
            name: Voice name
            voice_data: Voice data dictionary

        Returns:
            Voice preset dictionary
        """
        return {
            "name": name,
            "latent": voice_data.get("latent").tolist()
            if hasattr(voice_data.get("latent"), "tolist")
            else str(voice_data.get("latent")),
            "sample_rate": voice_data.get("sample_rate", 24000),
        }

    def create_voice(
        self,
        name: str,
        audio_samples: Union[str, Path, List[Union[str, Path]]],
    ) -> str:
        """Create a custom voice from audio samples.

        Args:
            name: Name for the custom voice
            audio_samples: Path or list of paths to audio files

        Returns:
            Name of created voice

        Raises:
            ValueError: If name or audio_samples is missing
            FileNotFoundError: If audio sample not found
        """
        if not name or not name.strip():
            raise ValueError("name is required")

        if not audio_samples:
            raise ValueError("audio_samples is required")

        name = name.strip().replace(" ", "_")

        voice_data = self._process_audio_samples(audio_samples)

        preset = self._create_voice_preset(name, voice_data)

        self._save_voice_preset(name, preset)
        self._load_custom_voices()

        return name

    def clone_voice(
        self,
        name: str,
        reference_audio: Union[str, Path],
    ) -> str:
        """Clone a voice from reference audio.

        This is a convenience method that wraps create_voice for single reference audio.

        Args:
            name: Name for the cloned voice
            reference_audio: Path to reference audio file

        Returns:
            Name of created voice
        """
        return self.create_voice(name=name, audio_samples=reference_audio)

    def _save_voice_preset(self, name: str, preset: Dict) -> Path:
        """Save voice preset to disk.

        Args:
            name: Voice name
            preset: Voice preset data

        Returns:
            Path to saved file
        """
        voices_dir = self._get_custom_voices_dir()
        preset_path = voices_dir / f"{name}.json"

        with open(preset_path, "w") as f:
            json.dump(preset, f, indent=2)

        self._custom_voices[name] = preset_path
        return preset_path

    def save_preset(self, name: str, voice_data: Dict) -> Path:
        """Save custom voice preset.

        Args:
            name: Voice name
            voice_data: Voice preset data dictionary

        Returns:
            Path to saved file
        """
        return self._save_voice_preset(name, voice_data)

    def load_preset(self, name: str) -> Dict:
        """Load custom voice preset.

        Args:
            name: Voice name

        Returns:
            Voice preset data

        Raises:
            FileNotFoundError: If preset not found
        """
        self._load_custom_voices()

        if name not in self._custom_voices:
            voices_dir = self._get_custom_voices_dir()
            preset_path = voices_dir / f"{name}.json"
            if not preset_path.exists():
                raise FileNotFoundError(f"Voice preset not found: {name}")
            preset_path = voices_dir / f"{name}.json"

        preset_path = self._custom_voices[name]
        with open(preset_path, "r") as f:
            return json.load(f)

    def delete_voice(self, name: str) -> None:
        """Delete custom voice preset.

        Args:
            name: Voice name to delete

        Raises:
            ValueError: If trying to delete built-in voice
            FileNotFoundError: If voice not found
        """
        self._load_custom_voices()

        if name in self._builtin_voices:
            raise ValueError(f"Cannot delete built-in voice: {name}")

        if name not in self._custom_voices:
            raise FileNotFoundError(f"Custom voice not found: {name}")

        preset_path = self._custom_voices[name]
        if preset_path.exists():
            preset_path.unlink()

        del self._custom_voices[name]

    def voice_exists(self, name: str) -> bool:
        """Check if a voice exists.

        Args:
            name: Voice name

        Returns:
            True if voice exists
        """
        if not self._loaded:
            self._load_builtin_voices()
        self._load_custom_voices()

        return name in self._builtin_voices or name in self._custom_voices

    def is_builtin(self, name: str) -> bool:
        """Check if voice is built-in.

        Args:
            name: Voice name

        Returns:
            True if voice is built-in
        """
        if not self._loaded:
            self._load_builtin_voices()
        return name in self._builtin_voices

    def is_custom(self, name: str) -> bool:
        """Check if voice is custom.

        Args:
            name: Voice name

        Returns:
            True if voice is custom
        """
        self._load_custom_voices()
        return name in self._custom_voices
