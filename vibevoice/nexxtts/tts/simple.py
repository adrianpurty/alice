"""Simple TTS Wrapper - Fluent interface for NexTTS"""

from __future__ import annotations

from typing import Optional
import numpy as np

from .client import NexTTS


_client: Optional[NexTTS] = None


def _get_client(
    model_path: Optional[str] = None,
    voice: Optional[str] = None,
    device: str = "auto",
    inference_steps: int = 5,
) -> NexTTS:
    """Get or create a singleton NexTTS client instance."""
    global _client

    if _client is None:
        if model_path is None:
            raise ValueError("model_path is required for the first TTS call")
        _client = NexTTS(
            model="realtime",
            voice=voice,
            device=device,
            model_path=model_path,
            inference_steps=inference_steps,
        )
        _client.load()

    return _client


def _reset_client() -> None:
    """Reset the singleton client (for testing)."""
    global _client
    _client = None


class TTS:
    """Simple TTS class for fluent text-to-speech generation.

    Provides a chainable interface for generating speech audio.

    Args:
        text: The text to synthesize
        voice: Voice preset name (optional, uses default if not specified)

    Example:
        >>> audio = TTS("Hello, world!").generate()
        >>> TTS("Hi").to_pcm16()  # Returns bytes
    """

    def __init__(
        self,
        text: str,
        voice: Optional[str] = None,
    ) -> None:
        self.text = text
        self._voice = voice

    def generate(
        self,
        model_path: Optional[str] = None,
        voice: Optional[str] = None,
        device: str = "auto",
        inference_steps: int = 5,
        **kwargs,
    ) -> np.ndarray:
        """Generate audio from the text.

        Args:
            model_path: Path to model (required on first call)
            voice: Voice preset to use
            device: Device for inference
            inference_steps: Number of diffusion steps
            **kwargs: Additional arguments passed to NexTTS.generate()

        Returns:
            numpy.ndarray: Audio as float32 array
        """
        client = _get_client(
            model_path=model_path,
            voice=voice or self._voice,
            device=device,
            inference_steps=inference_steps,
        )
        return client.generate(self.text, voice=voice or self._voice, **kwargs)

    def stream(self, **kwargs):
        """Stream audio from the text.

        Args:
            **kwargs: Arguments passed to NexTTS.stream()

        Yields:
            numpy.ndarray: Audio chunks
        """
        client = _get_client(voice=self._voice)
        yield from client.stream(self.text, **kwargs)

    def to_pcm16(self, **kwargs) -> bytes:
        """Generate audio and convert to PCM16 format.

        Args:
            **kwargs: Arguments passed to generate()

        Returns:
            bytes: Audio in PCM16 format
        """
        audio = self.generate(**kwargs)
        return _get_client().to_pcm16(audio)
