from core.errors import ServiceError


class TranscriberError(ServiceError):
    """
    Base for every error this service raises on purpose.
    """


class WhisperError(TranscriberError):
    """
    The ASR service could not be reached or returned an error.
    """


class DiarizerError(TranscriberError):
    """
    The diarizer service could not be reached, failed, or timed out.
    """


class LLMError(TranscriberError):
    """
    An LLM step could not run or returned unusable output.
    """


class ConversionError(TranscriberError):
    """
    An upload could not be converted into the audio the pipeline consumes.
    """
