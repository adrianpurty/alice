# vibevoice/__init__.py


def __getattr__(name):
    if name in (
        "VibeVoiceStreamingForConditionalGenerationInference",
        "VibeVoiceStreamingConfig",
    ):
        from vibevoice import modular

        return getattr(modular, name)
    if name in ("VibeVoiceStreamingProcessor", "VibeVoiceTokenizerProcessor"):
        from vibevoice import processor

        return getattr(processor, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return [
        "VibeVoiceStreamingForConditionalGenerationInference",
        "VibeVoiceStreamingConfig",
        "VibeVoiceStreamingProcessor",
        "VibeVoiceTokenizerProcessor",
    ]
