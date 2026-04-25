"""TTS Module - Text-to-Speech"""


def __getattr__(name):
    if name == "NexTTS":
        from .client import NexTTS

        return NexTTS
    elif name == "TTS":
        from .simple import TTS

        return TTS
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return ["NexTTS", "TTS"]
