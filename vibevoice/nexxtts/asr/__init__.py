"""ASR Module - NexTTS Automatic Speech Recognition"""


def __getattr__(name):
    if name == "ASR":
        from .client import ASR

        return ASR
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return ["ASR"]
