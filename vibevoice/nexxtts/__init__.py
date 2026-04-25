"""NexTTS - Voice AI Integration Platform (vibevoice subpackage)

A library for integrating TTS and ASR capabilities into applications.
"""

__version__ = "0.1.0"


def __getattr__(name):
    if name in ("NexTTS", "TTS"):
        from vibevoice.nexxtts import tts

        return getattr(tts, name)
    if name == "ASR":
        from . import asr

        return getattr(asr, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return ["NexTTS", "TTS", "ASR", "__version__"]
