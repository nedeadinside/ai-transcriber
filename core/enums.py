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


class MediaFormat(StrEnum):
    """
    Audio or video container/extension accepted for upload.
    """

    WAV = "wav"
    MP3 = "mp3"
    M4A = "m4a"
    FLAC = "flac"
    OGG = "ogg"
    OGA = "oga"
    OPUS = "opus"
    AAC = "aac"
    WMA = "wma"
    AMR = "amr"
    AIFF = "aiff"
    AIF = "aif"
    MKA = "mka"
    CAF = "caf"

    MP4 = "mp4"
    M4V = "m4v"
    MOV = "mov"
    MKV = "mkv"
    WEBM = "webm"
    AVI = "avi"
    WMV = "wmv"
    FLV = "flv"
    MPG = "mpg"
    MPEG = "mpeg"
    TS = "ts"
    MTS = "mts"
    THREE_GP = "3gp"


class JobState(StrEnum):
    """
    Lifecycle state of a queued job.
    """

    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
