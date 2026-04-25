"""Tests for ASR Client Module"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestASRClientInterface:
    """Test suite for ASR client interface"""

    def test_asr_has_required_methods(self):
        """Test ASR class has load and transcribe methods"""
        from vibevoice.nexxtts.asr.client import ASR

        assert hasattr(ASR, "load")
        assert hasattr(ASR, "transcribe")
        assert callable(getattr(ASR, "load"))
        assert callable(getattr(ASR, "transcribe"))

    def test_asr_has_streaming_method(self):
        """Test ASR has transcribe_streaming method"""
        from vibevoice.nexxtts.asr.client import ASR

        assert hasattr(ASR, "transcribe_streaming")

    def test_asr_init_signature(self):
        """Test ASR __init__ accepts device and model_path"""
        from vibevoice.nexxtts.asr.client import ASR
        import inspect

        sig = inspect.signature(ASR.__init__)
        params = list(sig.parameters.keys())

        assert "device" in params
        assert "model_path" in params


class TestASRClientTranscribeOutput:
    """Test transcribe output structure"""

    def test_transcribe_returns_dict_with_text_and_segments(self):
        """Test transcribe returns dict with text and segments keys"""
        from vibevoice.nexxtts.asr.client import ASR

        mock_model = MagicMock()
        mock_processor = MagicMock()
        mock_processor.pad_id = 151643
        mock_processor.tokenizer.eos_token_id = 151643

        with patch.object(ASR, "load"):
            client = ASR(model_path="test/path")
            client._model = mock_model
            client._processor = mock_processor
            client._device = MagicMock()
            client._resolved_device = "cpu"
            client._loaded = True

            mock_output = MagicMock()
            mock_output.shape = (1, 100)
            mock_model.generate.return_value = mock_output
            mock_model.device = MagicMock()
            mock_processor.decode.return_value = '[{"start_time": 0.0, "end_time": 1.0, "speaker_id": "SPEAKER_1", "text": "Hello world"}]'
            mock_processor.post_process_transcription.return_value = [
                {
                    "start_time": 0.0,
                    "end_time": 1.0,
                    "speaker_id": "SPEAKER_1",
                    "text": "Hello world",
                }
            ]

            result = client.transcribe("test.wav")

            assert isinstance(result, dict)
            assert "text" in result
            assert "segments" in result
            assert isinstance(result["segments"], list)

    def test_transcribe_segments_have_required_fields(self):
        """Test segments have required fields"""
        from vibevoice.nexxtts.asr.client import ASR

        mock_model = MagicMock()
        mock_processor = MagicMock()
        mock_processor.pad_id = 151643
        mock_processor.tokenizer.eos_token_id = 151643

        with patch.object(ASR, "load"):
            client = ASR(model_path="test/path")
            client._model = mock_model
            client._processor = mock_processor
            client._device = MagicMock()
            client._resolved_device = "cpu"
            client._loaded = True

            mock_output = MagicMock()
            mock_output.shape = (1, 100)
            mock_model.generate.return_value = mock_output
            mock_model.device = MagicMock()
            mock_processor.decode.return_value = '[{"start_time": 0.0, "end_time": 1.0, "speaker_id": "SPEAKER_1", "text": "Hello world"}]'
            mock_processor.post_process_transcription.return_value = [
                {
                    "start_time": 0.0,
                    "end_time": 1.0,
                    "speaker_id": "SPEAKER_1",
                    "text": "Hello world",
                }
            ]

            result = client.transcribe("test.wav")

            segments = result["segments"]
            assert len(segments) > 0
            seg = segments[0]
            assert "start" in seg or "start_time" in seg
            assert "end" in seg or "end_time" in seg
            assert "text" in seg or "content" in seg
            assert "speaker" in seg or "speaker_id" in seg


class TestASRClientHotwords:
    """Test hotwords support"""

    def test_transcribe_accepts_hotwords(self):
        """Test transcribe accepts hotwords parameter"""
        from vibevoice.nexxtts.asr.client import ASR

        mock_model = MagicMock()
        mock_processor = MagicMock()
        mock_processor.pad_id = 151643
        mock_processor.tokenizer.eos_token_id = 151643

        with patch.object(ASR, "load"):
            client = ASR(model_path="test/path")
            client._model = mock_model
            client._processor = mock_processor
            client._device = MagicMock()
            client._resolved_device = "cpu"
            client._loaded = True

            mock_output = MagicMock()
            mock_output.shape = (1, 100)
            mock_model.generate.return_value = mock_output
            mock_model.device = MagicMock()
            mock_processor.decode.return_value = "Test transcription"
            mock_processor.post_process_transcription.return_value = []

            hotwords = {"vibevoice": "VibeVoice", "AI": "Artificial Intelligence"}

            result = client.transcribe("test.wav", hotwords=hotwords)

            assert isinstance(result, dict)


class TestASRValidation:
    """Test input validation"""

    def test_transcribe_empty_path_raises(self):
        """Test transcribe with empty path raises error"""
        from vibevoice.nexxtts.asr.client import ASR

        with patch.object(ASR, "load"):
            client = ASR(model_path="test/path")
            client._model = MagicMock()
            client._processor = MagicMock()
            client._device = MagicMock()
            client._resolved_device = "cpu"
            client._loaded = True

            with pytest.raises(ValueError, match="audio_path"):
                client.transcribe("")

    def test_load_without_model_path_raises(self):
        """Test load raises error without model_path"""
        from vibevoice.nexxtts.asr.client import ASR

        client = ASR()
        with pytest.raises(ValueError, match="model_path"):
            client.load()


class TestASRAutoLoad:
    """Test auto-load feature"""

    def test_transcribe_auto_loads_when_not_loaded(self):
        """Test transcribe auto-loads model when not loaded"""
        from vibevoice.nexxtts.asr.client import ASR

        mock_model = MagicMock()
        mock_processor = MagicMock()
        mock_processor.pad_id = 151643
        mock_processor.tokenizer.eos_token_id = 151643

        with patch.object(ASR, "load") as mock_load:
            client = ASR(model_path="test/path")
            client._model = mock_model
            client._processor = mock_processor
            client._device = MagicMock()
            client._resolved_device = "cpu"
            client._loaded = False

            mock_output = MagicMock()
            mock_output.shape = (1, 100)
            mock_model.generate.return_value = mock_output
            mock_model.device = MagicMock()
            mock_processor.decode.return_value = "Test"
            mock_processor.post_process_transcription.return_value = []

            result = client.transcribe("test.wav")

            assert mock_load.called


class TestASRModuleExports:
    """Test module exports"""

    def test_asr_init_exports_asr(self):
        """Test asr __init__.py exports ASR"""
        from vibevoice.nexxtts.asr import ASR

        assert ASR is not None
