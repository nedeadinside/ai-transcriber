import asyncio
import uuid
from http import HTTPStatus
from pathlib import Path
from typing import IO, TYPE_CHECKING, Final

from fastapi import HTTPException, UploadFile

from enums import AudioFormat

if TYPE_CHECKING:
    from config.models import AppConfig

_BYTES_PER_MB: Final[int] = 1024 * 1024
_CHUNK: Final[int] = _BYTES_PER_MB


class AudioSpool:
    """
    Validates and stores uploaded audio files in the spool directory.
    """

    def __init__(self, cfg: "AppConfig") -> None:
        """
        Store settings used to validate and place uploads.

        :param cfg: Root settings.
        """
        self.cfg = cfg

    async def save(self, file: UploadFile) -> str:
        """
        Save the uploaded file to the spool directory.

        :param file: Uploaded file.
        :raises HTTPException: If the format is invalid or the size limit is exceeded.
        :return: Absolute path to the saved file.
        """
        ext = self._validate_extension(file.filename, self.cfg.audio.allowed_formats)
        spool_dir = Path(self.cfg.audio.spool_dir)
        path = spool_dir / f"{uuid.uuid4().hex}.{ext}"
        limit = self.cfg.audio.max_upload_mb * _BYTES_PER_MB

        await asyncio.to_thread(
            self._write_spooled, file.file, spool_dir, path, limit, self.cfg.audio.max_upload_mb
        )
        await asyncio.to_thread(self._validate_duration, path, self.cfg.audio.max_duration_sec)
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
        :raises HTTPException: If the size limit is exceeded.
        """
        spool_dir.mkdir(parents=True, exist_ok=True)
        size = 0
        with path.open("wb") as out:
            while chunk := source.read(_CHUNK):
                size += len(chunk)
                if size > limit:
                    out.close()
                    path.unlink()
                    raise HTTPException(
                        status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                        detail=f"file exceeds {limit_mb} MB",
                    )
                out.write(chunk)

    @staticmethod
    def _validate_duration(path: Path, max_duration_sec: int) -> None:
        """
        Probe duration and enforce the configured limit.

        :param path: Path to the spooled file.
        :param max_duration_sec: Maximum allowed duration in seconds.
        :raises HTTPException: If the file is not readable audio or exceeds the limit.
        """
        import torchaudio  # noqa: PLC0415

        try:
            info = torchaudio.info(str(path))
            duration = info.num_frames / info.sample_rate
        except RuntimeError:
            path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="unreadable audio file",
            ) from None

        if duration > max_duration_sec:
            path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                detail=f"duration exceeds {max_duration_sec}s",
            )

    @staticmethod
    def _validate_extension(filename: str, allowed: list[AudioFormat]) -> AudioFormat:
        """
        Validate the file extension and return it normalized.

        :param filename: Name of the uploaded file.
        :param allowed: Allowed extensions without the dot.
        :raises HTTPException: If the extension is missing or not allowed.
        :return: Lowercased extension without the dot.
        """
        ext = Path(filename or "").suffix.lower().lstrip(".")
        try:
            fmt = AudioFormat(ext)
        except ValueError:
            fmt = None
        if fmt is None or fmt not in allowed:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"unsupported format '{ext}', allowed: {allowed}",
            )
        return fmt
