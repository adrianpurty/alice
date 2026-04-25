"""ASR Client - NexTTS Automatic Speech Recognition Client"""

from __future__ import annotations

from typing import Dict, Optional, Any, Iterator

import torch

from vibevoice.modular.modeling_vibevoice_asr import (
    VibeVoiceASRForConditionalGeneration,
)
from vibevoice.processor.vibevoice_asr_processor import VibeVoiceASRProcessor


class ASR:
    """NexTTS ASR Client for automatic speech recognition.

    Supports long-form audio transcription (up to 60 min), custom hotwords,
    speaker diarization, and timestamps.

    Args:
        device: Device for inference - 'auto', 'cuda', 'cpu', 'mps' (default: 'auto')
        model_path: Path to model or HuggingFace repo ID
    """

    def __init__(
        self,
        device: str = "auto",
        model_path: Optional[str] = None,
    ) -> None:
        self.device = device
        self.model_path = model_path

        self._resolved_device = self._resolve_device(device)
        self._torch_device = torch.device(self._resolved_device)

        self.processor: Optional[VibeVoiceASRProcessor] = None
        self._model: Optional[VibeVoiceASRForConditionalGeneration] = None
        self._loaded = False
        self._hotwords: Dict[str, str] = {}

    def _resolve_device(self, device: str) -> str:
        """Resolve device with auto-detection support."""
        if device == "mps":
            if not torch.backends.mps.is_available():
                print("Warning: MPS not available. Falling back to CPU.")
                return "cpu"
            return device
        if device == "cuda":
            if not torch.cuda.is_available():
                print("Warning: CUDA not available. Falling back to CPU.")
                return "cpu"
            return device
        if device != "auto":
            return device

        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def load(self) -> None:
        """Load model and processor.

        Raises:
            ValueError: If model_path is not set
            RuntimeError: If model loading fails
        """
        if not self.model_path:
            raise ValueError("model_path is required to load the model")

        if self._loaded:
            return

        self.processor = VibeVoiceASRProcessor.from_pretrained(self.model_path)

        if self._resolved_device == "mps":
            load_dtype = torch.float32
            device_map = None
            attn_impl = "sdpa"
        elif self._resolved_device == "cuda":
            load_dtype = torch.bfloat16
            device_map = "cuda"
            attn_impl = "flash_attention_2"
        else:
            load_dtype = torch.float32
            device_map = "cpu"
            attn_impl = "sdpa"

        try:
            self._model = VibeVoiceASRForConditionalGeneration.from_pretrained(
                self.model_path,
                torch_dtype=load_dtype,
                device_map=device_map,
                attn_implementation=attn_impl,
                trust_remote_code=True,
            )
        except Exception as e:
            if attn_impl == "flash_attention_2":
                self._model = VibeVoiceASRForConditionalGeneration.from_pretrained(
                    self.model_path,
                    torch_dtype=load_dtype,
                    device_map=self._resolved_device,
                    attn_implementation="sdpa",
                    trust_remote_code=True,
                )
            else:
                raise e

        if self._resolved_device != "auto":
            self._model = self._model.to(self._resolved_device)

        self._model.eval()
        self._loaded = True

    def transcribe(
        self,
        audio_path: str,
        hotwords: Optional[Dict[str, str]] = None,
        max_new_tokens: int = 32768,
        temperature: float = 0.0,
        top_p: float = 1.0,
        auto_load: bool = True,
    ) -> Dict[str, Any]:
        """Transcribe audio file to text with timestamps and speaker diarization.

        Args:
            audio_path: Path to audio file (supports common formats: wav, mp3, flac, etc.)
            hotwords: Optional dict of custom hotwords to boost recognition
                   e.g., {"vibevoice": "VibeVoice", "AI": "Artificial Intelligence"}
            max_new_tokens: Maximum tokens to generate
            temperature: Temperature for sampling (0 = greedy)
            top_p: Nucleus sampling parameter
            auto_load: Automatically load model if not loaded (default: True)

        Returns:
            dict with:
                - text: Full transcription text
                - segments: List of segments with start, end, text, speaker
        """
        if not audio_path:
            raise ValueError("audio_path is required")

        if not self._loaded:
            if auto_load and self.model_path:
                self.load()
            else:
                raise RuntimeError("Model not loaded. Call load() first.")

        audio_path = str(audio_path)

        context_info = None
        if hotwords:
            hotwords_str = ", ".join(f"{k}: {v}" for k, v in hotwords.items())
            context_info = f"Hotwords: {hotwords_str}"

        inputs = self.processor(
            audio=audio_path,
            sampling_rate=None,
            return_tensors="pt",
            padding=True,
            add_generation_prompt=True,
            context_info=context_info,
        )

        inputs = {
            k: v.to(self._resolved_device) if hasattr(v, "to") else v
            for k, v in inputs.items()
        }

        generation_config = {
            "max_new_tokens": max_new_tokens,
            "pad_token_id": self.processor.pad_id,
            "eos_token_id": self.processor.tokenizer.eos_token_id,
            "do_sample": temperature > 0,
            "temperature": temperature if temperature > 0 else 1.0,
            "top_p": top_p,
        }

        with torch.no_grad():
            output_ids = self._model.generate(
                **inputs,
                **generation_config,
            )

        input_length = inputs["input_ids"].shape[1]
        generated_ids = output_ids[0, input_length:]

        eos_positions = (
            generated_ids == self.processor.tokenizer.eos_token_id
        ).nonzero(as_tuple=True)[0]
        if len(eos_positions) > 0:
            generated_ids = generated_ids[: eos_positions[0] + 1]

        generated_text = self.processor.decode(generated_ids, skip_special_tokens=True)

        segments = self.processor.post_process_transcription(generated_text)

        formatted_segments = []
        for seg in segments:
            formatted_seg = {
                "start": seg.get("start_time", seg.get("start", 0.0)),
                "end": seg.get("end_time", seg.get("end", 0.0)),
                "text": seg.get("text", seg.get("content", "")),
                "speaker": seg.get("speaker_id", seg.get("speaker", "SPEAKER_1")),
            }
            formatted_segments.append(formatted_seg)

        full_text = " ".join(seg["text"] for seg in formatted_segments)

        return {
            "text": full_text,
            "segments": formatted_segments,
        }

    def transcribe_streaming(
        self,
        audio_path: str,
        hotwords: Optional[Dict[str, str]] = None,
        max_new_tokens: int = 32768,
        temperature: float = 0.0,
        top_p: float = 1.0,
    ) -> Iterator[Dict[str, Any]]:
        """Transcribe audio with streaming results (yields segments as they are generated).

        For long audio files, processes in chunks and yields segments progressively.

        Args:
            audio_path: Path to audio file
            hotwords: Optional custom hotwords
            max_new_tokens: Maximum tokens to generate
            temperature: Temperature for sampling
            top_p: Nucleus sampling parameter

        Yields:
            dict with segment information
        """
        result = self.transcribe(
            audio_path=audio_path,
            hotwords=hotwords,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
        )

        for segment in result["segments"]:
            yield segment
