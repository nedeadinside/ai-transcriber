import asyncio
import uuid
from pathlib import Path
from typing import IO, TYPE_CHECKING, Final

from core.enums import MediaFormat
from core.errors import AudioError, AudioTooLargeError

if TYPE_CHECKING:
    from fastapi import UploadFile

    from core.config.models import AudioConfig

_BYTES_PER_MB: Final[int] = 1024 * 1024
_CHUNK: Final[int] = _BYTES_PER_MB


class AudioSpool:
    """
    Validates and stores uploaded audio files in the spool directory.
    """

    def __init__(self, cfg: "AudioConfig") -> None:
        """
        Store settings used to validate and place uploads.

        :param cfg: Audio settings.
        """
        self.cfg = cfg

    async def save(self, file: "UploadFile") -> str:
        """
        Save the uploaded file to the spool directory.

        :param file: Uploaded file.
        :raises AudioError: If the format is invalid or the audio is unreadable.
        :raises AudioTooLargeError: If the size or duration limit is exceeded.
        :return: Absolute path to the saved file.
        """
        ext = self._validate_extension(file.filename, self.cfg.allowed_formats)
        spool_dir = Path(self.cfg.spool_dir)
        path = spool_dir / f"{uuid.uuid4().hex}.{ext}"
        limit = self.cfg.max_upload_mb * _BYTES_PER_MB

        await asyncio.to_thread(
            self._write_spooled, file.file, spool_dir, path, limit, self.cfg.max_upload_mb
        )
        await asyncio.to_thread(self._validate_duration, path, self.cfg.max_duration_sec)
        return str(path)

    @staticmethod
    def _write_spooled(
        source: IO[bytes], spool_dir: Path, path: Path, limit: int, limit_mb: int
    ) -> None:
        """
        Stream the source file to the spool path, enforcing the size limit.

        :param source: Sync file-like object backing the upload.
        :param spool_dir: Directory to create if missing.
        :param path: Destination path for the spooled file.
        :param limit: Maximum allowed size in bytes.
        :param limit_mb: Maximum allowed size in MB, for the error message.
        :raises AudioTooLargeError: If the size limit is exceeded.
        """
        spool_dir.mkdir(parents=True, exist_ok=True)
        size = 0
        with path.open("wb") as out:
            while chunk := source.read(_CHUNK):
                size += len(chunk)
                if size > limit:
                    out.close()
                    path.unlink()
                    raise AudioTooLargeError(f"file exceeds {limit_mb} MB")
                out.write(chunk)

    @staticmethod
    def _validate_duration(path: Path, max_duration_sec: int) -> None:
        """
        Probe duration and the audio track, enforcing the configured limit.

        :param path: Path to the spooled file.
        :param max_duration_sec: Maximum allowed duration in seconds.
        :raises AudioError: If the file is not readable media or carries no audio track.
        :raises AudioTooLargeError: If the duration limit is exceeded.
        """
        import av  # noqa: PLC0415

        try:
            with av.open(str(path)) as container:
                raw_duration = container.duration
                has_audio = bool(container.streams.audio)
        except av.FFmpegError:
            raw_duration = None

        if raw_duration is None:
            path.unlink(missing_ok=True)
            raise AudioError("unreadable audio file")

        if not has_audio:
            path.unlink(missing_ok=True)
            raise AudioError("no audio track")

        if raw_duration / av.time_base > max_duration_sec:
            path.unlink(missing_ok=True)
            raise AudioTooLargeError(f"duration exceeds {max_duration_sec}s")

    @staticmethod
    def _validate_extension(filename: str, allowed: list[MediaFormat]) -> MediaFormat:
        """
        Validate the file extension and return it normalized.

        :param filename: Name of the uploaded file.
        :param allowed: Allowed extensions without the dot.
        :raises AudioError: If the extension is missing or not allowed.
        :return: Lowercased extension without the dot.
        """
        ext = Path(filename or "").suffix.lower().lstrip(".")
        try:
            fmt = MediaFormat(ext)
        except ValueError:
            fmt = None
        if fmt is None or fmt not in allowed:
            raise AudioError(f"unsupported format '{ext}', allowed: {', '.join(allowed)}")
        return fmt
