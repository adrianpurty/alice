import grpc
import os
from typing import Iterator, Dict, Any, Optional, List

try:
    from cloud.proto import nexxtts_pb2, nexxtts_pb2_grpc
except ImportError:
    from nexxtts_cloud.proto import nexxtts_pb2, nexxtts_pb2_grpc


class NexTTSCloud:
    def __init__(
        self,
        api_key: str,
        endpoint: Optional[str] = None,
        secure: bool = True,
    ):
        self.api_key = api_key
        self.endpoint = endpoint or os.environ.get(
            "NEXTTTS_ENDPOINT", "api.nexxtts.cloud:443"
        )
        self.secure = secure
        self._channel = None
        self._stub = None

    def _get_channel(self) -> grpc.Channel:
        if self._channel is None:
            if self.secure:
                credentials = grpc.ssl_channel_credentials()
                call_credentials = grpc.access_token_call_credentials(self.api_key)
                composite_credentials = grpc.composite_channel_credentials(
                    credentials, call_credentials
                )
                self._channel = grpc.secure_channel(
                    self.endpoint, composite_credentials
                )
            else:
                self._channel = grpc.insecure_channel(self.endpoint)
            self._stub = nexxtts_pb2_grpc.NexTTSStub(self._channel)
        return self._channel

    @property
    def stub(self) -> nexxtts_pb2_grpc.NexTTSStub:
        if self._stub is None:
            self._get_channel()
        return self._stub

    def stream(
        self,
        text: str,
        voice: str = "en-Carter",
        inference_steps: Optional[int] = None,
        temperature: Optional[float] = None,
        cfg_scale: Optional[float] = None,
    ) -> Iterator[nexxtts_pb2.AudioChunk]:
        request = nexxtts_pb2.StreamTTSRequest(
            text=text,
            voice=voice,
        )
        if inference_steps is not None:
            request.inference_steps = inference_steps
        if temperature is not None:
            request.temperature = temperature
        if cfg_scale is not None:
            request.cfg_scale = cfg_scale

        try:
            for chunk in self.stub.StreamTTS(request):
                yield chunk
        except grpc.RpcError as e:
            raise NexTTSError(f"Stream failed: {e.code().name}: {e.details()}") from e

    def generate(
        self,
        text: str,
        voice: str = "en-Carter",
        format: str = "wav",
    ) -> nexxtts_pb2.GenerateTTSResponse:
        request = nexxtts_pb2.GenerateTTSRequest(
            text=text,
            voice=voice,
            format=format,
        )

        try:
            return self.stub.GenerateTTS(request)
        except grpc.RpcError as e:
            raise NexTTSError(f"Generate failed: {e.code().name}: {e.details()}") from e

    def transcribe(
        self,
        audio_data: bytes,
        hotwords: Optional[Dict[str, str]] = None,
        include_timestamps: bool = False,
        include_speakers: bool = False,
    ) -> Dict[str, Any]:
        request = nexxtts_pb2.TranscribeRequest(
            audio_data=audio_data,
            include_timestamps=include_timestamps,
            include_speakers=include_speakers,
        )
        if hotwords:
            request.hotwords.update(hotwords)

        try:
            response = self.stub.Transcribe(request)
            return {
                "text": response.text,
                "segments": [
                    {
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text,
                        "speaker": seg.speaker,
                    }
                    for seg in response.segments
                ],
            }
        except grpc.RpcError as e:
            raise NexTTSError(
                f"Transcribe failed: {e.code().name}: {e.details()}"
            ) from e

    def list_voices(self) -> List[Dict[str, Any]]:
        request = nexxtts_pb2.ListVoicesRequest()

        try:
            response = self.stub.ListVoices(request)
            return [
                {"name": voice.name, "is_builtin": voice.is_builtin}
                for voice in response.voices
            ]
        except grpc.RpcError as e:
            raise NexTTSError(
                f"ListVoices failed: {e.code().name}: {e.details()}"
            ) from e

    def create_voice(
        self,
        name: str,
        audio_samples: List[bytes],
    ) -> Dict[str, Any]:
        request = nexxtts_pb2.CreateVoiceRequest(
            name=name,
            audio_samples=audio_samples,
        )

        try:
            response = self.stub.CreateVoice(request)
            return {"name": response.name, "is_builtin": response.is_builtin}
        except grpc.RpcError as e:
            raise NexTTSError(
                f"CreateVoice failed: {e.code().name}: {e.details()}"
            ) from e

    def delete_voice(self, name: str) -> None:
        request = nexxtts_pb2.DeleteVoiceRequest(name=name)

        try:
            self.stub.DeleteVoice(request)
        except grpc.RpcError as e:
            raise NexTTSError(
                f"DeleteVoice failed: {e.code().name}: {e.details()}"
            ) from e

    def close(self) -> None:
        if self._channel:
            self._channel.close()
            self._channel = None
            self._stub = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class NexTTSError(Exception):
    pass
