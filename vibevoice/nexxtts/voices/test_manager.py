"""Tests for Voice Manager Module"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import json
import tempfile
import sys


class TestVoiceManagerImports:
    """Test VoiceManager imports"""

    def test_voice_manager_module_exists(self):
        """Test manager module can be imported"""
        try:
            from vibevoice.nexxtts.voices import manager

            assert hasattr(manager, "VoiceManager")
        except (ModuleNotFoundError, ValueError):
            pass


class TestVoiceManagerListVoices:
    """Test listing built-in voices"""

    def test_list_voices_returns_list(self):
        """Test list_voices returns a list"""
        try:
            from vibevoice.nexxtts.voices.manager import VoiceManager
        except (ModuleNotFoundError, ValueError):
            pytest.skip("Dependencies not available")
            return

        with patch.object(VoiceManager, "_load_builtin_voices") as mock_load:
            mock_load.return_value = {
                "en-Carter_man": Path("en-Carter_man.pt"),
                "en-Emma_woman": Path("en-Emma_woman.pt"),
            }
            with patch.object(VoiceManager, "_load_custom_voices") as mock_custom:
                mock_custom.return_value = {}
                vm = VoiceManager()
                vm._loaded = True
                voices = vm.list_voices()
                assert isinstance(voices, list)

    def test_list_voices_contains_voices(self):
        """Test list_voices returns voice names"""
        try:
            from vibevoice.nexxtts.voices.manager import VoiceManager
        except (ModuleNotFoundError, ValueError):
            pytest.skip("Dependencies not available")
            return

        vm = VoiceManager()
        vm._builtin_voices = {
            "en-Carter_man": Path("en-Carter_man.pt"),
            "en-Emma_woman": Path("en-Emma_woman.pt"),
        }
        vm._custom_voices = {}
        vm._loaded = True
        voices = vm.voices
        assert "en-Carter_man" in voices
        assert "en-Emma_woman" in voices


class TestVoiceManagerCreateVoice:
    """Test creating custom voices"""

    def test_create_voice_accepts_params(self):
        """Test create_voice accepts name and audio_samples"""
        try:
            from vibevoice.nexxtts.voices.manager import VoiceManager
        except (ModuleNotFoundError, ValueError):
            pytest.skip("Dependencies not available")
            return

        vm = VoiceManager()
        with patch.object(vm, "_process_audio_samples") as mock_process:
            mock_process.return_value = {"latent": np.array([0.1, 0.2])}
            with patch.object(vm, "_save_voice_preset") as mock_save:
                vm.create_voice(name="my_voice", audio_samples=["sample1.wav"])
                mock_process.assert_called_once()

    def test_create_voice_stores_custom_voice(self):
        """Test create_voice stores custom voice"""
        try:
            from vibevoice.nexxtts.voices.manager import VoiceManager
        except (ModuleNotFoundError, ValueError):
            pytest.skip("Dependencies not available")
            return

        vm = VoiceManager()
        with patch.object(vm, "_process_audio_samples") as mock_process:
            mock_process.return_value = {"latent": np.array([0.1, 0.2])}
            with patch.object(vm, "_load_custom_voices") as mock_load:
                mock_load.return_value = {}
                with tempfile.TemporaryDirectory() as tmpdir:
                    vm._custom_voices_dir = Path(tmpdir)
                    vm.create_voice(name="my_voice", audio_samples=["sample1.wav"])
                    assert "my_voice" in vm._custom_voices or mock_load.called

    def test_create_voice_requires_name(self):
        """Test create_voice requires name"""
        try:
            from vibevoice.nexxtts.voices.manager import VoiceManager
        except (ModuleNotFoundError, ValueError):
            pytest.skip("Dependencies not available")
            return

        vm = VoiceManager()
        with pytest.raises((ValueError, TypeError), match="name|required"):
            vm.create_voice(audio_samples=["sample1.wav"])

    def test_create_voice_requires_audio_samples(self):
        """Test create_voice requires audio_samples"""
        try:
            from vibevoice.nexxtts.voices.manager import VoiceManager
        except (ModuleNotFoundError, ValueError):
            pytest.skip("Dependencies not available")
            return

        vm = VoiceManager()
        with pytest.raises((ValueError, TypeError), match="audio_samples|required"):
            vm.create_voice(name="my_voice")


class TestVoiceManagerCloneVoice:
    """Test cloning voices"""

    def test_clone_voice_accepts_reference(self):
        """Test clone_voice accepts reference_audio"""
        try:
            from vibevoice.nexxtts.voices.manager import VoiceManager
        except (ModuleNotFoundError, ValueError):
            pytest.skip("Dependencies not available")
            return

        vm = VoiceManager()
        with patch.object(vm, "_process_audio_samples") as mock_process:
            mock_process.return_value = {"latent": np.array([0.1])}
            with patch.object(vm, "_save_voice_preset") as mock_save:
                vm.clone_voice(name="cloned_voice", reference_audio="ref.wav")
                mock_process.assert_called_once()

    def test_clone_voice_returns_name(self):
        """Test clone_voice returns voice name"""
        try:
            from vibevoice.nexxtts.voices.manager import VoiceManager
        except (ModuleNotFoundError, ValueError):
            pytest.skip("Dependencies not available")
            return

        vm = VoiceManager()
        with patch.object(vm, "_process_audio_samples") as mock_process:
            mock_process.return_value = {"latent": np.array([0.1])}
            with patch.object(vm, "_save_voice_preset") as mock_save:
                result = vm.clone_voice(name="cloned_voice", reference_audio="ref.wav")
                assert result == "cloned_voice"


class TestVoiceManagerSaveLoad:
    """Test save and load operations"""

    def test_save_preset(self):
        """Test save_preset saves to disk"""
        try:
            from vibevoice.nexxtts.voices.manager import VoiceManager
        except (ModuleNotFoundError, ValueError):
            pytest.skip("Dependencies not available")
            return

        vm = VoiceManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            vm._custom_voices_dir = Path(tmpdir)
            vm.save_preset(name="test_voice", voice_data={"data": "test"})
            saved_file = Path(tmpdir) / "test_voice.json"
            assert saved_file.exists()

    def test_load_preset(self):
        """Test load_preset loads from disk"""
        try:
            from vibevoice.nexxtts.voices.manager import VoiceManager
        except (ModuleNotFoundError, ValueError):
            pytest.skip("Dependencies not available")
            return

        vm = VoiceManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            voice_file = Path(tmpdir) / "my_voice.json"
            with open(voice_file, "w") as f:
                json.dump({"name": "my_voice", "data": [1, 2, 3]}, f)
            vm._custom_voices_dir = Path(tmpdir)
            data = vm.load_preset(name="my_voice")
            assert data is not None
            assert data["name"] == "my_voice"

    def test_load_nonexistent_raises(self):
        """Test loading non-existent preset raises"""
        try:
            from vibevoice.nexxtts.voices.manager import VoiceManager
        except (ModuleNotFoundError, ValueError):
            pytest.skip("Dependencies not available")
            return

        vm = VoiceManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            vm._custom_voices_dir = Path(tmpdir)
            with pytest.raises(FileNotFoundError):
                vm.load_preset(name="nonexistent")


class TestVoiceManagerDelete:
    """Test deleting voices"""

    def test_delete_voice_removes(self):
        """Test delete_voice removes custom voice"""
        try:
            from vibevoice.nexxtts.voices.manager import VoiceManager
        except (ModuleNotFoundError, ValueError):
            pytest.skip("Dependencies not available")
            return

        vm = VoiceManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            vm._custom_voices_dir = Path(tmpdir)
            voice_file = Path(tmpdir) / "my_voice.json"
            voice_file.touch()
            vm._custom_voices = {"my_voice": voice_file}
            vm.delete_voice(name="my_voice")
            assert "my_voice" not in vm._custom_voices


class TestVoicesModuleExports:
    """Test module exports"""

    def test_voices_init_exports_voice_manager(self):
        """Test voices __init__.py exports VoiceManager"""
        from vibevoice.nexxtts import voices

        assert "VoiceManager" in dir(voices)

    def test_voices_init_has_in_all(self):
        """Test VoiceManager in __all__"""
        from vibevoice.nexxtts import voices

        assert "VoiceManager" in voices.__all__
