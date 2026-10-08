import asyncio
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Final, Protocol

from core.enums import MediaFormat
from errors import ConversionError

if TYPE_CHECKING:
    from av.audio.stream import AudioStream
    from av.container import InputContainer

SAMPLE_RATE: Final[int] = 16000


class Converter(Protocol):
    """
    Strategy that turns one kind of upload into the audio the pipeline consumes.
    """

    def convert(self, src: Path, dst: Path, stop: threading.Event) -> None:
        """
        Write src to dst as FLAC, 16 kHz, mono.

        :param src: Uploaded file.
        :param dst: Destination path for the converted audio.
        :param stop: Set by the caller to abort; checked between packets.
        :raises ConversionError: If the file cannot be converted or the conversion is aborted.
        """


_REGISTRY: dict[MediaFormat, Converter] = {}


def register[C: Converter](*formats: MediaFormat) -> Callable[[type[C]], type[C]]:
    """
    Register a converter class as the strategy for the given formats.

    :param formats: Formats the class handles.
    :return: Class decorator that stores one instance per format.
    """

    def decorator(cls: type[C]) -> type[C]:
        """
        Store an instance of the class under each format.

        :param cls: Converter class.
        :return: The class, unchanged.
        """
        instance = cls()
        for fmt in formats:
            _REGISTRY[fmt] = instance
        return cls

    return decorator


def get(fmt: MediaFormat) -> Converter:
    """
    Return the converter registered for a format.

    :param fmt: Format of the upload.
    :raises ConversionError: If no converter handles the format.
    :return: The registered converter.
    """
    try:
        return _REGISTRY[fmt]
    except KeyError:
        raise ConversionError(f"no converter for format '{fmt}'") from None


def formats() -> set[MediaFormat]:
    """
    Return every format a converter is registered for.

    :return: Registered formats.
    """
    return set(_REGISTRY)


@register(
    MediaFormat.WAV,
    MediaFormat.MP3,
    MediaFormat.M4A,
    MediaFormat.FLAC,
    MediaFormat.OGG,
    MediaFormat.OGA,
    MediaFormat.OPUS,
    MediaFormat.AAC,
    MediaFormat.WMA,
    MediaFormat.AMR,
    MediaFormat.AIFF,
    MediaFormat.AIF,
    MediaFormat.MKA,
    MediaFormat.CAF,
)
class AudioTranscoder:
    """
    Decodes the first audio stream and re-encodes it as FLAC, 16 kHz, mono.
    """

    def convert(self, src: Path, dst: Path, stop: threading.Event) -> None:
        """
        Write src to dst as FLAC, 16 kHz, mono.

        :param src: Uploaded file.
        :param dst: Destination path for the converted audio.
        :param stop: Set by the caller to abort; checked between packets.
        :raises ConversionError: If the file cannot be converted or the conversion is aborted.
        """
        import av  # noqa: PLC0415

        try:
            self._transcode(src, dst, stop)
        except av.FFmpegError as e:
            dst.unlink(missing_ok=True)
            raise ConversionError(f"cannot convert {src.name}: {e}") from e
        except ConversionError:
            dst.unlink(missing_ok=True)
            raise

    def _transcode(self, src: Path, dst: Path, stop: threading.Event) -> None:
        """
        Decode the picked stream, resample it and mux it into a FLAC file.

        :param src: Uploaded file.
        :param dst: Destination path for the converted audio.
        :param stop: Set by the caller to abort; checked between packets.
        :raises ConversionError: If there is no audio track or the conversion is aborted.
        """
        import av  # noqa: PLC0415

        with av.open(str(src)) as source, av.open(str(dst), "w", format="flac") as out:
            stream = self._pick_stream(source)
            encoder = out.add_stream("flac", rate=SAMPLE_RATE, layout="mono")
            resampler = av.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
            for packet in source.demux(stream):
                if stop.is_set():
                    raise ConversionError("conversion aborted")
                for frame in packet.decode():
                    for chunk in resampler.resample(frame):
                        out.mux(encoder.encode(chunk))
            for chunk in resampler.resample(None):
                out.mux(encoder.encode(chunk))
            out.mux(encoder.encode(None))

    def _pick_stream(self, container: "InputContainer") -> "AudioStream":
        """
        Choose the audio stream to convert.

        :param container: Opened upload.
        :raises ConversionError: If the file carries no audio stream.
        :return: The first audio stream.
        """
        if not container.streams.audio:
            raise ConversionError("no audio track")
        return container.streams.audio[0]


@register(
    MediaFormat.MP4,
    MediaFormat.M4V,
    MediaFormat.MOV,
    MediaFormat.MKV,
    MediaFormat.WEBM,
    MediaFormat.AVI,
    MediaFormat.WMV,
    MediaFormat.FLV,
    MediaFormat.MPG,
    MediaFormat.MPEG,
    MediaFormat.TS,
    MediaFormat.MTS,
    MediaFormat.THREE_GP,
)
class VideoAudioExtractor(AudioTranscoder):
    """
    Pulls the main audio track out of a video container; video packets are never decoded.
    """

    def _pick_stream(self, container: "InputContainer") -> "AudioStream":
        """
        Choose the main audio track, skipping commentary or dubbed tracks.

        :param container: Opened upload.
        :raises ConversionError: If the video carries no audio track.
        :return: The audio stream ffmpeg ranks best.
        """
        stream = container.streams.best("audio")
        if stream is None:
            raise ConversionError("no audio track")
        return stream


async def to_flac(src: Path, dst: Path) -> None:
    """
    Convert an upload to FLAC, 16 kHz, mono, with the strategy registered for its extension.

    The conversion runs in a thread; on cancellation the thread is told to stop at its next
    packet, so it neither outlives the job for long nor leaves dst behind.

    :param src: Uploaded file in the spool.
    :param dst: Destination path for the converted audio.
    :raises ConversionError: If the format is unknown or the file cannot be converted.
    """
    try:
        fmt = MediaFormat(src.suffix.lower().lstrip("."))
    except ValueError:
        raise ConversionError(f"unsupported format '{src.suffix}'") from None

    stop = threading.Event()
    try:
        await asyncio.to_thread(get(fmt).convert, src, dst, stop)
    except asyncio.CancelledError:
        stop.set()
        raise
