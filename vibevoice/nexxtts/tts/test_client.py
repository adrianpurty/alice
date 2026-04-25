"""Tests for NexTTS Client Module"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestNexTTSClient:
    """Test suite for NexTTS client functionality"""

    def test_client_initialization(self):
        """Test client can be initialized with required parameters"""
        from vibevoice.nexxtts.tts.client import NexTTS

        client = NexTTS(
            model="realtime",
            voice="en-Carter_man",
            device="auto",
            model_path="test/path",
            inference_steps=5,
        )

        assert client.model == "realtime"
        assert client.voice == "en-Carter_man"
        assert client.device == "auto"
        assert client.model_path == "test/path"
        assert client.inference_steps == 5

    def test_client_initialization_defaults(self):
        """Test client has sensible defaults"""
        from vibevoice.nexxtts.tts.client import NexTTS

        client = NexTTS(model_path="test/path")

        assert client.model == "realtime"
        assert client.device == "auto"
        assert client.inference_steps == 5

    def test_device_auto_detection_cuda(self):
        """Test device auto-detection prefers CUDA when available"""
        from vibevoice.nexxtts.tts.client import NexTTS

        with patch("torch.cuda.is_available", return_value=True):
            client = NexTTS(model_path="test/path", device="auto")
            assert client._resolved_device == "cuda"

    def test_device_auto_detection_mps(self):
        """Test device auto-detection falls back to MPS when CUDA unavailable"""
        from vibevoice.nexxtts.tts.client import NexTTS

        with patch("torch.cuda.is_available", return_value=False):
            with patch("torch.backends.mps.is_available", return_value=True):
                client = NexTTS(model_path="test/path", device="auto")
                assert client._resolved_device == "mps"

    def test_device_auto_detection_cpu(self):
        """Test device auto-detection falls back to CPU when no GPU available"""
        from vibevoice.nexxtts.tts.client import NexTTS

        with patch("torch.cuda.is_available", return_value=False):
            with patch("torch.backends.mps.is_available", return_value=False):
                client = NexTTS(model_path="test/path", device="auto")
                assert client._resolved_device == "cpu"

    def test_voices_property(self):
        """Test voices property returns list of available voices"""
        from vibevoice.nexxtts.tts.client import NexTTS

        with patch.object(NexTTS, "load"):
            client = NexTTS(model_path="test/path", voice="en-Carter_man")
            client._voice_presets = {
                "en-Carter_man": Path("test1.pt"),
                "en-Emma_woman": Path("test2.pt"),
            }

            voices = client.voices
            assert "en-Carter_man" in voices
            assert "en-Emma_woman" in voices
            assert len(voices) == 2

    def test_load_without_model_path_raises(self):
        """Test load raises error without model_path"""
        from vibevoice.nexxtts.tts.client import NexTTS

        client = NexTTS()
        with pytest.raises(ValueError, match="model_path"):
            client.load()

    def test_generate_returns_numpy_float32(self):
        """Test generate method returns numpy.float32 array"""
        from vibevoice.nexxtts.tts.client import NexTTS

        mock_model = MagicMock()
        mock_model.generate.return_value = iter(
            [np.array([0.1, 0.2, 0.3], dtype=np.float32)]
        )

        with patch.object(NexTTS, "load"):
            client = NexTTS(model_path="test/path", voice="en-Carter_man")
            client._model = mock_model
            client._processor = MagicMock()
            client._voice_cache = {"en-Carter_man": MagicMock()}
            client._default_voice_key = "en-Carter_man"
            client._torch_device = MagicMock()
            client._sample_rate = 24000

            audio = client.generate("Hello world")

            assert isinstance(audio, np.ndarray)
            assert audio.dtype == np.float32

    def test_stream_yields_numpy_chunks(self):
        """Test stream method yields numpy.float32 chunks"""
        from vibevoice.nexxtts.tts.client import NexTTS

        mock_model = MagicMock()
        mock_model.generate.return_value = iter(
            [np.array([0.1, 0.2, 0.3], dtype=np.float32)]
        )

        with patch.object(NexTTS, "load"):
            client = NexTTS(model_path="test/path", voice="en-Carter_man")
            client._model = mock_model
            client._processor = MagicMock()
            client._voice_cache = {"en-Carter_man": MagicMock()}
            client._default_voice_key = "en-Carter_man"
            client._torch_device = MagicMock()
            client._sample_rate = 24000

            chunks = list(client.stream("Hello world"))

            assert len(chunks) == 1
            assert isinstance(chunks[0], np.ndarray)
            assert chunks[0].dtype == np.float32

    def test_stream_with_custom_voice(self):
        """Test stream accepts custom voice key"""
        from vibevoice.nexxtts.tts.client import NexTTS

        with patch.object(NexTTS, "load"):
            client = NexTTS(model_path="test/path", voice="en-Carter_man")
            client._voice_presets = {
                "en-Carter_man": Path("test1.pt"),
                "custom_voice": Path("test2.pt"),
            }
            client._voice_cache = {"custom_voice": MagicMock()}
            client._default_voice_key = "en-Carter_man"
            client._model = MagicMock()
            client._processor = MagicMock()
            client._torch_device = MagicMock()
            client._sample_rate = 24000

            list(client.stream("Hello", voice="custom_voice"))

            assert "custom_voice" in client._voice_cache

    def test_generate_empty_text_returns_empty(self):
        """Test generate with empty text returns empty array"""
        from vibevoice.nexxtts.tts.client import NexTTS

        with patch.object(NexTTS, "load"):
            client = NexTTS(model_path="test/path")
            audio = client.generate("")

            assert isinstance(audio, np.ndarray)
            assert audio.size == 0


class TestSimpleTTS:
    """Test suite for Simple TTS wrapper"""

    def test_simple_tts_initialization(self):
        """Test SimpleTTS can be instantiated with text"""
        from vibevoice.nexxtts.tts.simple import TTS

        tts = TTS("Hello world")
        assert tts.text == "Hello world"

    def test_simple_tts_generate_method(self):
        """Test SimpleTTS generate returns numpy array"""
        from vibevoice.nexxtts.tts.simple import TTS

        mock_audio = np.array([0.1, 0.2, 0.3], dtype=np.float32)

        with patch("vibevoice.nexxtts.tts.simple._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate.return_value = mock_audio
            mock_get_client.return_value = mock_client

            tts = TTS("Hello world")
            audio = tts.generate()

            assert isinstance(audio, np.ndarray)
            assert audio.dtype == np.float32
            mock_client.generate.assert_called_once_with("Hello world")

    def test_simple_tts_chainable(self):
        """Test SimpleTTS is chainable"""
        from vibevoice.nexxtts.tts.simple import TTS

        mock_audio = np.array([0.1], dtype=np.float32)

        with patch("vibevoice.nexxtts.tts.simple._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate.return_value = mock_audio
            mock_get_client.return_value = mock_client

            audio = TTS("Hello").generate()
            assert isinstance(audio, np.ndarray)

    def test_simple_tts_respects_voice(self):
        """Test SimpleTTS uses configured voice"""
        from vibevoice.nexxtts.tts.simple import TTS

        with patch("vibevoice.nexxtts.tts.simple._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.generate.return_value = np.array([0.1], dtype=np.float32)
            mock_get_client.return_value = mock_client

            TTS("Hello", voice="custom_voice").generate()

            call_kwargs = mock_client.generate.call_args
            assert (
                call_kwargs[1].get("voice") == "custom_voice"
                or mock_client.default_voice == "custom_voice"
            )


class TestNexTTSModuleExports:
    """Test module exports"""

    def test_tts_init_exports_nexitts(self):
        """Test tts __init__.py exports NexTTS"""
        from vibevoice.nexxtts.tts import NexTTS

        assert NexTTS is not None

    def test_simple_tts_exports(self):
        """Test simple.py exports TTS class"""
        from vibevoice.nexxtts.tts.simple import TTS

        assert TTS is not None
