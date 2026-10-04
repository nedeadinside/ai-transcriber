from enum import StrEnum


class LogLevel(StrEnum):
    """
    Logging verbosity level.
    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AudioFormat(StrEnum):
    """
    Audio container/extension accepted for upload.
    """

    WAV = "wav"
    MP3 = "mp3"
    M4A = "m4a"
    FLAC = "flac"
    OGG = "ogg"


class JobState(StrEnum):
    """
    Lifecycle state of a queued job.
    """

    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
