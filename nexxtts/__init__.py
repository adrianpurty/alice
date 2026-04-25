"""NexTTS - Voice AI Integration Platform

A library for integrating TTS and ASR capabilities into applications.
"""

__version__ = "0.1.0"


def __getattr__(name):
    if name == "TTS":
        from vibevoice.nexxtts.tts.simple import TTS

        return TTS
    elif name == "NexTTS":
        from vibevoice.nexxtts.tts.client import NexTTS

        return NexTTS
    elif name == "ASR":
        from vibevoice.nexxtts.asr.client import ASR

        return ASR
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return ["TTS", "NexTTS", "ASR", "__version__"]
