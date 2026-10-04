class ServiceError(Exception):
    """
    Base for every error a service raises on purpose.
    """


class AudioError(ServiceError):
    """
    An upload that cannot be accepted.
    """


class AudioTooLargeError(AudioError):
    """
    An upload that exceeds the configured size or duration cap.
    """
