"""gRPC handlers for NexTTS service."""

from __future__ import annotations

import io
from typing import Iterator, Optional, Tuple

import numpy as np

try:
    from proto import nexxtts_pb2
    from proto import nexxtts_pb2_grpc
except ImportError:
    from cloud.proto import nexxtts_pb2
    from cloud.proto import nexxtts_pb2_grpc

try:
    from cloud.auth.jwt import require_auth
except ImportError:
    require_auth = lambda f: f

try:
    from core.db import create_repository
    from core.security.rate_limit import RateLimiter
except ImportError:
    create_repository = None
    RateLimiter = None


def _check_rate_limit(context, endpoint: str) -> Tuple[bool, Optional[str]]:
    """Check rate limit for the request."""
    if create_repository is None or RateLimiter is None:
        return True, None

    user_id = context.get("user_id")
    if not user_id:
        return True, None

    repo = None
    try:
        repo, _ = create_repository()
        limiter = RateLimiter(repo)
        allowed, reason = limiter.check_limit(user_id, endpoint)
        return allowed, reason
    except Exception:
        return True, None
    finally:
        if repo:
            repo.close()


class NexTTTServicer(nexxtts_pb2_grpc.NexTTSServicer):
    """gRPC service implementation for NexTTS."""

    def __init__(self):
        self._tts = None
        self._asr = None
        self._voices_dir = None
        self._custom_voices = {}

    @property
    def tts(self):
        """Lazy-load TTS client."""
        if self._tts is None:
            from vibevoice.nexxtts.tts import NexTTS

            self._tts = NexTTS()
        return self._tts

    @property
    def asr(self):
        """Lazy-load ASR client."""
        if self._asr is None:
            from vibevoice.nexxtts.asr import ASR

            self._asr = ASR()
        return self._asr

    def _ensure_tts_loaded(self):
        """Ensure TTS is loaded."""
        if not self.tts._loaded:
            self.tts.load()

    @require_auth
    def StreamTTS(
        self,
        request: nexxtts_pb2.StreamTTSRequest,
        context,
    ) -> Iterator[nexxtts_pb2.AudioChunk]:
        """Stream audio chunks for TTS request."""
        allowed, reason = _check_rate_limit(context, "tts_stream")
        if not allowed:
            context.abort(16, reason or "Rate limit exceeded")

        self._ensure_tts_loaded()

        stream = self.tts.stream(
            text=request.text,
            voice=request.voice,
            inference_steps=request.inference_steps,
            temperature=request.temperature,
            cfg_scale=request.cfg_scale,
        )

        for chunk in stream:
            pcm_data = self.tts.to_pcm16(chunk)
            yield nexxtts_pb2.AudioChunk(
                pcm_data=pcm_data,
                sample_rate=self.tts._sample_rate,
                is_final=False,
            )

        yield nexxtts_pb2.AudioChunk(
            pcm_data=b"",
            sample_rate=self.tts._sample_rate,
            is_final=True,
        )

    @require_auth
    def GenerateTTS(
        self,
        request: nexxtts_pb2.GenerateTTSRequest,
        context,
    ) -> nexxtts_pb2.GenerateTTSResponse:
        """Generate full audio for TTS request."""
        allowed, reason = _check_rate_limit(context, "tts_generate")
        if not allowed:
            context.abort(16, reason or "Rate limit exceeded")

        self._ensure_tts_loaded()

        audio = self.tts.generate(
            text=request.text,
            voice=request.voice,
            inference_steps=50,
        )

        pcm_data = self.tts.to_pcm16(audio)
        duration_sec = len(audio) / self.tts._sample_rate

        return nexxtts_pb2.GenerateTTSResponse(
            audio_data=pcm_data,
            format=request.format or "pcm16",
            duration_sec=int(duration_sec),
        )

    @require_auth
    def Transcribe(
        self,
        request: nexxtts_pb2.TranscribeRequest,
        context,
    ) -> nexxtts_pb2.TranscribeResponse:
        """Transcribe audio data."""
        allowed, reason = _check_rate_limit(context, "asr_transcribe")
        if not allowed:
            context.abort(16, reason or "Rate limit exceeded")

        audio = (
            np.frombuffer(request.audio_data, dtype=np.int16).astype(np.float32)
            / 32767.0
        )

        result = self.asr.transcribe(
            audio=audio,
            hotwords=dict(request.hotwords) if request.hotwords else None,
            include_timestamps=request.include_timestamps,
            include_speakers=request.include_speakers,
        )

        segments = []
        if result.get("segments"):
            for seg in result["segments"]:
                segments.append(
                    nexxtts_pb2.TranscribeResponse.Segment(
                        start=seg.get("start", 0.0),
                        end=seg.get("end", 0.0),
                        text=seg.get("text", ""),
                        speaker=seg.get("speaker", ""),
                    )
                )

        return nexxtts_pb2.TranscribeResponse(
            text=result.get("text", ""),
            segments=segments,
        )

    @require_auth
    def ListVoices(
        self,
        request: nexxtts_pb2.ListVoicesRequest,
        context,
    ) -> nexxtts_pb2.ListVoicesResponse:
        """List available voices."""
        self._ensure_tts_loaded()

        voice_names = self.tts.voices
        voices = [nexxtts_pb2.Voice(name=name, is_builtin=True) for name in voice_names]

        for name in self._custom_voices:
            voices.append(nexxtts_pb2.Voice(name=name, is_builtin=False))

        return nexxtts_pb2.ListVoicesResponse(voices=voices)

    @require_auth
    def CreateVoice(
        self,
        request: nexxtts_pb2.CreateVoiceRequest,
        context,
    ) -> nexxtts_pb2.Voice:
        """Create a custom voice."""
        if request.name in self._custom_voices:
            raise ValueError(f"Voice {request.name!r} already exists")

        self._custom_voices[request.name] = list(request.audio_samples)

        return nexxtts_pb2.Voice(name=request.name, is_builtin=False)

    @require_auth
    def DeleteVoice(
        self,
        request: nexxtts_pb2.DeleteVoiceRequest,
        context,
    ) -> nexxtts_pb2.Empty:
        """Delete a custom voice."""
        if request.name not in self._custom_voices:
            raise ValueError(f"Voice {request.name!r} not found")

        del self._custom_voices[request.name]

        return nexxtts_pb2.Empty()


def add_NexTTSServicer_to_server(servicer, server):
    """Add servicer to gRPC server."""
    nexxtts_pb2_grpc.add_NexTTSServicer_to_server(servicer, server)
