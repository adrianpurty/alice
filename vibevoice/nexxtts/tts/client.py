"""NexTTS Client - Full-featured TTS client with OOP design"""

from __future__ import annotations

import copy
import os
import threading
import traceback
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple, Any, Callable

import numpy as np
import torch

from vibevoice.modular.modeling_vibevoice_streaming_inference import (
    VibeVoiceStreamingForConditionalGenerationInference,
)
from vibevoice.modular.streamer import AudioStreamer
from vibevoice.processor.vibevoice_streaming_processor import (
    VibeVoiceStreamingProcessor,
)


SAMPLE_RATE = 24_000
VOICES_DIR = Path(__file__).parent.parent / "voices" / "streaming_model"


class NexTTS:
    """Full-featured NexTTS Client for text-to-speech generation.

    Supports both batch generation and streaming with customizable voices,
    device selection, and inference parameters.

    Args:
        model: Model type - 'realtime', 'batch', or 'asr' (default: 'realtime')
        voice: Voice preset name (default: 'en-Carter_man')
        device: Device for inference - 'auto', 'cuda', 'cpu', 'mps' (default: 'auto')
        model_path: Path to model or HuggingFace repo ID
        inference_steps: Number of diffusion steps (default: 5)
    """

    def __init__(
        self,
        model: str = "realtime",
        voice: Optional[str] = None,
        device: str = "auto",
        model_path: Optional[str] = None,
        inference_steps: int = 5,
    ) -> None:
        self.model = model
        self.voice = voice
        self.inference_steps = inference_steps
        self.model_path = model_path

        self._resolved_device = self._resolve_device(device)
        self._torch_device = torch.device(self._resolved_device)

        self.processor: Optional[VibeVoiceStreamingProcessor] = None
        self.model_instance: Optional[
            VibeVoiceStreamingForConditionalGenerationInference
        ] = None
        self._voice_presets: Dict[str, Path] = {}
        self._default_voice_key: Optional[str] = None
        self._voice_cache: Dict[str, Any] = {}
        self._sample_rate = SAMPLE_RATE
        self._loaded = False

    def _resolve_device(self, device: str) -> str:
        """Resolve device with auto-detection support."""
        if device != "auto":
            if device in ("mpx", "mps") and device == "mpx":
                device = "mps"
            if device == "mps" and not torch.backends.mps.is_available():
                print("Warning: MPS not available. Falling back to CPU.")
                return "cpu"
            return device

        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    @property
    def voices(self) -> List[str]:
        """Return list of available voice presets."""
        if not self._voice_presets:
            self._load_voice_presets()
        return sorted(self._voice_presets.keys())

    @property
    def default_voice(self) -> Optional[str]:
        """Return the default voice key."""
        return self._default_voice_key

    @property
    def device(self) -> str:
        """Return the resolved device string."""
        return self._resolved_device

    def _load_voice_presets(self) -> Dict[str, Path]:
        """Load available voice presets from voices directory."""
        if not VOICES_DIR.exists():
            raise RuntimeError(f"Voices directory not found: {VOICES_DIR}")

        presets: Dict[str, Path] = {}
        for pt_path in VOICES_DIR.rglob("*.pt"):
            presets[pt_path.stem] = pt_path

        if not presets:
            raise RuntimeError(f"No voice preset (.pt) files found in {VOICES_DIR}")

        self._voice_presets = dict(sorted(presets.items()))
        return self._voice_presets

    def _determine_voice_key(self, name: Optional[str]) -> str:
        """Determine which voice preset to use."""
        if name and name in self._voice_presets:
            return name

        default_key = self.voice or "en-Carter_man"
        if default_key in self._voice_presets:
            return default_key

        first_key = next(iter(self._voice_presets))
        print(f"Using fallback voice preset: {first_key}")
        return first_key

    def _ensure_voice_cached(self, key: str) -> Any:
        """Ensure voice preset is loaded and cached."""
        if key not in self._voice_presets:
            raise RuntimeError(f"Voice preset {key!r} not found")

        if key not in self._voice_cache:
            preset_path = self._voice_presets[key]
            prefilled_outputs = torch.load(
                preset_path,
                map_location=self._torch_device,
                weights_only=False,
            )
            self._voice_cache[key] = prefilled_outputs

        return self._voice_cache[key]

    def _get_voice_resources(self, requested_key: Optional[str]) -> Tuple[str, Any]:
        """Get voice resources for generation."""
        key = (
            requested_key
            if requested_key and requested_key in self._voice_presets
            else self._default_voice_key
        )
        if key is None:
            key = next(iter(self._voice_presets))
            self._default_voice_key = key

        prefilled_outputs = self._ensure_voice_cached(key)
        return key, prefilled_outputs

    def _prepare_inputs(self, text: str, prefilled_outputs: Any) -> Dict[str, Any]:
        """Prepare model inputs from text and voice preset."""
        if not self.processor or not self.model_instance:
            raise RuntimeError("NexTTS client not loaded. Call load() first.")

        processed = self.processor.process_input_with_cached_prompt(
            text=text.strip(),
            cached_prompt=prefilled_outputs,
            padding=True,
            return_tensors="pt",
            return_attention_mask=True,
        )

        prepared = {
            key: value.to(self._torch_device) if hasattr(value, "to") else value
            for key, value in processed.items()
        }
        return prepared

    def _run_generation(
        self,
        inputs: Dict[str, Any],
        audio_streamer: AudioStreamer,
        errors: List[Exception],
        cfg_scale: float,
        do_sample: bool,
        temperature: float,
        top_p: float,
        refresh_negative: bool,
        prefilled_outputs: Any,
        stop_event: threading.Event,
    ) -> None:
        """Run model generation in background thread."""
        try:
            self.model_instance.generate(
                **inputs,
                max_new_tokens=None,
                cfg_scale=cfg_scale,
                tokenizer=self.processor.tokenizer,
                generation_config={
                    "do_sample": do_sample,
                    "temperature": temperature if do_sample else 1.0,
                    "top_p": top_p if do_sample else 1.0,
                },
                audio_streamer=audio_streamer,
                stop_check_fn=stop_event.is_set,
                verbose=False,
                refresh_negative=refresh_negative,
                all_prefilled_outputs=copy.deepcopy(prefilled_outputs),
            )
        except Exception as exc:
            errors.append(exc)
            traceback.print_exc()
            audio_streamer.end()

    def load(self) -> None:
        """Load model and processor.

        Raises:
            ValueError: If model_path is not set
            RuntimeError: If model loading fails
        """
        if not self.model_path:
            raise ValueError("model_path is required to load the model")

        self.processor = VibeVoiceStreamingProcessor.from_pretrained(self.model_path)

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
            self.model_instance = (
                VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                    self.model_path,
                    torch_dtype=load_dtype,
                    device_map=device_map,
                    attn_implementation=attn_impl,
                )
            )

            if self._resolved_device == "mps":
                self.model_instance.to("mps")
        except Exception as e:
            if attn_impl == "flash_attention_2":
                self.model_instance = (
                    VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                        self.model_path,
                        torch_dtype=load_dtype,
                        device_map=self._resolved_device,
                        attn_implementation="sdpa",
                    )
                )
            else:
                raise e

        self.model_instance.eval()

        self.model_instance.model.noise_scheduler = (
            self.model_instance.model.noise_scheduler.from_config(
                self.model_instance.model.noise_scheduler.config,
                algorithm_type="sde-dpmsolver++",
                beta_schedule="squaredcos_cap_v2",
            )
        )
        self.model_instance.set_ddpm_inference_steps(num_steps=self.inference_steps)

        self._load_voice_presets()
        self._default_voice_key = self._determine_voice_key(self.voice)
        self._ensure_voice_cached(self._default_voice_key)

        self._loaded = True

    def generate(
        self,
        text: str,
        cfg_scale: float = 1.5,
        do_sample: bool = False,
        temperature: float = 0.9,
        top_p: float = 0.9,
        refresh_negative: bool = True,
        inference_steps: Optional[int] = None,
        voice: Optional[str] = None,
    ) -> np.ndarray:
        """Generate full audio from text.

        Args:
            text: Input text to synthesize
            cfg_scale: Classifier-free guidance scale
            do_sample: Whether to use sampling
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            refresh_negative: Whether to refresh negative prompts
            inference_steps: Override inference steps
            voice: Voice preset to use

        Returns:
            numpy.ndarray: Audio as float32 array
        """
        if not text.strip():
            return np.array([], dtype=np.float32)

        text = text.replace("'", "'").replace("'", "'")

        selected_voice, prefilled_outputs = self._get_voice_resources(voice)

        steps_to_use = inference_steps or self.inference_steps
        if steps_to_use > 0 and self.model_instance:
            self.model_instance.set_ddpm_inference_steps(num_steps=steps_to_use)

        inputs = self._prepare_inputs(text, prefilled_outputs)
        audio_streamer = AudioStreamer(batch_size=1, stop_signal=None, timeout=None)
        errors: List[Exception] = []
        stop_signal = threading.Event()

        thread = threading.Thread(
            target=self._run_generation,
            kwargs={
                "inputs": inputs,
                "audio_streamer": audio_streamer,
                "errors": errors,
                "cfg_scale": cfg_scale,
                "do_sample": do_sample,
                "temperature": temperature,
                "top_p": top_p,
                "refresh_negative": refresh_negative,
                "prefilled_outputs": prefilled_outputs,
                "stop_event": stop_signal,
            },
            daemon=True,
        )
        thread.start()

        audio_chunks: List[np.ndarray] = []

        try:
            stream = audio_streamer.get_stream(0)
            for audio_chunk in stream:
                if torch.is_tensor(audio_chunk):
                    audio_chunk = audio_chunk.detach().cpu().to(torch.float32).numpy()
                else:
                    audio_chunk = np.asarray(audio_chunk, dtype=np.float32)

                if audio_chunk.ndim > 1:
                    audio_chunk = audio_chunk.reshape(-1)

                peak = np.max(np.abs(audio_chunk)) if audio_chunk.size else 0.0
                if peak > 1.0:
                    audio_chunk = audio_chunk / peak

                audio_chunks.append(audio_chunk.astype(np.float32, copy=False))
        finally:
            stop_signal.set()
            audio_streamer.end()
            thread.join()
            if errors:
                raise errors[0]

        if not audio_chunks:
            return np.array([], dtype=np.float32)

        return np.concatenate(audio_chunks)

    def stream(
        self,
        text: str,
        cfg_scale: float = 1.5,
        do_sample: bool = False,
        temperature: float = 0.9,
        top_p: float = 0.9,
        refresh_negative: bool = True,
        inference_steps: Optional[int] = None,
        voice: Optional[str] = None,
    ) -> Iterator[np.ndarray]:
        """Stream audio chunks from text.

        Args:
            text: Input text to synthesize
            cfg_scale: Classifier-free guidance scale
            do_sample: Whether to use sampling
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            refresh_negative: Whether to refresh negative prompts
            inference_steps: Override inference steps
            voice: Voice preset to use

        Yields:
            numpy.ndarray: Audio chunks as float32 arrays
        """
        if not text.strip():
            return

        text = text.replace("'", "'").replace("'", "'")

        selected_voice, prefilled_outputs = self._get_voice_resources(voice)

        steps_to_use = inference_steps or self.inference_steps
        if steps_to_use > 0 and self.model_instance:
            self.model_instance.set_ddpm_inference_steps(num_steps=steps_to_use)

        inputs = self._prepare_inputs(text, prefilled_outputs)
        audio_streamer = AudioStreamer(batch_size=1, stop_signal=None, timeout=None)
        errors: List[Exception] = []
        stop_signal = threading.Event()

        thread = threading.Thread(
            target=self._run_generation,
            kwargs={
                "inputs": inputs,
                "audio_streamer": audio_streamer,
                "errors": errors,
                "cfg_scale": cfg_scale,
                "do_sample": do_sample,
                "temperature": temperature,
                "top_p": top_p,
                "refresh_negative": refresh_negative,
                "prefilled_outputs": prefilled_outputs,
                "stop_event": stop_signal,
            },
            daemon=True,
        )
        thread.start()

        try:
            stream = audio_streamer.get_stream(0)
            for audio_chunk in stream:
                if torch.is_tensor(audio_chunk):
                    audio_chunk = audio_chunk.detach().cpu().to(torch.float32).numpy()
                else:
                    audio_chunk = np.asarray(audio_chunk, dtype=np.float32)

                if audio_chunk.ndim > 1:
                    audio_chunk = audio_chunk.reshape(-1)

                peak = np.max(np.abs(audio_chunk)) if audio_chunk.size else 0.0
                if peak > 1.0:
                    audio_chunk = audio_chunk / peak

                yield audio_chunk.astype(np.float32, copy=False)
        finally:
            stop_signal.set()
            audio_streamer.end()
            thread.join()
            if errors:
                raise errors[0]

    def to_pcm16(self, audio: np.ndarray) -> bytes:
        """Convert float32 audio to PCM16 bytes.

        Args:
            audio: Audio array (float32, range [-1, 1])

        Returns:
            bytes: PCM16 audio data
        """
        audio = np.clip(audio, -1.0, 1.0)
        pcm = (audio * 32767.0).astype(np.int16)
        return pcm.tobytes()
