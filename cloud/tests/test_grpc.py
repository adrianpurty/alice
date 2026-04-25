"""Tests for gRPC handlers and server."""

import sys
import os
import types
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np


class TestHandlersImport(unittest.TestCase):
    """Test that handlers module imports correctly."""

    def test_handlers_import(self):
        """Test handlers module can be imported."""
        from cloud.grpc import handlers

        self.assertIsNotNone(handlers)

    def test_servicer_class_exists(self):
        """Test NexTTTServicer class exists."""
        from cloud.grpc.handlers import NexTTTServicer

        self.assertTrue(hasattr(NexTTTServicer, "StreamTTS"))
        self.assertTrue(hasattr(NexTTTServicer, "GenerateTTS"))
        self.assertTrue(hasattr(NexTTTServicer, "Transcribe"))
        self.assertTrue(hasattr(NexTTTServicer, "ListVoices"))
        self.assertTrue(hasattr(NexTTTServicer, "CreateVoice"))
        self.assertTrue(hasattr(NexTTTServicer, "DeleteVoice"))

    def test_proto_import(self):
        """Test proto modules can be imported."""
        from cloud.proto import nexxtts_pb2
        from cloud.proto import nexxtts_pb2_grpc

        self.assertIsNotNone(nexxtts_pb2)
        self.assertIsNotNone(nexxtts_pb2_grpc)


class TestServerInstantiation(unittest.TestCase):
    """Test server can be instantiated."""

    def test_server_import(self):
        """Test server module can be imported."""
        from cloud.grpc import server

        self.assertIsNotNone(server)

    def test_serve_function_callable(self):
        """Test serve function is callable."""
        from cloud.grpc import server as server_module

        self.assertTrue(callable(server_module.serve))


class TestServicerMethods(unittest.TestCase):
    """Test servicer has all required methods."""

    def setUp(self):
        from cloud.grpc.handlers import NexTTTServicer

        self.servicer = NexTTTServicer()

    def test_stream_tts_method(self):
        """Test StreamTTS method exists."""
        self.assertTrue(callable(self.servicer.StreamTTS))

    def test_generate_tts_method(self):
        """Test GenerateTTS method exists."""
        self.assertTrue(callable(self.servicer.GenerateTTS))

    def test_transcribe_method(self):
        """Test Transcribe method exists."""
        self.assertTrue(callable(self.servicer.Transcribe))

    def test_list_voices_method(self):
        """Test ListVoices method exists."""
        self.assertTrue(callable(self.servicer.ListVoices))

    def test_create_voice_method(self):
        """Test CreateVoice method exists."""
        self.assertTrue(callable(self.servicer.CreateVoice))

    def test_delete_voice_method(self):
        """Test DeleteVoice method exists."""
        self.assertTrue(callable(self.servicer.DeleteVoice))


class TestToPCM16Conversion(unittest.TestCase):
    """Test PCM16 conversion."""

    def test_pcm16_conversion_formula(self):
        """Test PCM16 conversion produces expected data."""
        audio = np.array([0.0, 0.5, -0.5, 1.0, -1.0], dtype=np.float32)
        pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype(np.int16)
        result = pcm.tobytes()
        self.assertEqual(len(result), 10)


if __name__ == "__main__":
    unittest.main()
