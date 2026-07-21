import logging
from typing import TYPE_CHECKING, Final

from core.api.schemas import SpeakerSegment
from core.errors import AudioError

if TYPE_CHECKING:
    from pyannote.audio import Pipeline
    from pyannote.core import Annotation
    from torch import Tensor

    from config.models import AppConfig

logger = logging.getLogger(__name__)

_TIMESTAMP_NDIGITS: Final[int] = 3
_SAMPLE_RATE: Final[int] = 16000


def load_waveform(path: str) -> "Tensor":
    """
    Decode an audio file into the mono waveform pyannote expects.

    :param path: Path to the audio file.
    :raises AudioError: If the file holds no decodable audio.
    :return: Waveform of shape (channel, time) at _SAMPLE_RATE.
    """
    import av  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415
    import torch  # noqa: PLC0415

    resampler = av.AudioResampler(format="flt", layout="mono", rate=_SAMPLE_RATE)
    chunks: list[np.ndarray] = []
    with av.open(path) as container:
        for frame in container.decode(audio=0):
            chunks += [out.to_ndarray() for out in resampler.resample(frame)]
        chunks += [out.to_ndarray() for out in resampler.resample(None)]

    if not chunks:
        raise AudioError("no decodable audio stream")
    return torch.from_numpy(np.concatenate(chunks, axis=1))


def to_segments(annotation: "Annotation") -> list[SpeakerSegment]:
    """
    Convert a diarization result into a list of segments.

    :param annotation: Result produced by the pipeline.
    :return: List of segments with start, end, and speaker fields.
    """
    return [
        SpeakerSegment(
            start=round(segment.start, _TIMESTAMP_NDIGITS),
            end=round(segment.end, _TIMESTAMP_NDIGITS),
            speaker=speaker,
        )
        for segment, _, speaker in annotation.itertracks(yield_label=True)
    ]


class DiarizationPipeline:
    """
    Loaded pyannote pipeline bound to a configured inference device.
    """

    def __init__(self, cfg: "AppConfig") -> None:
        """
        Store settings and the inference device.

        :param cfg: Root settings.
        """
        import torch  # noqa: PLC0415

        self.cfg = cfg
        self.device = torch.device(cfg.inference.device)
        self.pipeline: Pipeline | None = None

    def load(self) -> None:
        """
        Load the pretrained pipeline and move it to the resolved device.
        """
        from pyannote.audio import Pipeline  # noqa: PLC0415

        self.pipeline = Pipeline.from_pretrained(
            self.cfg.model.checkpoint,
            token=self.cfg.model.auth_token,
        )
        self.pipeline.to(self.device)
        logger.info("pyannote pipeline loaded on device: %s", self.device)

    def run(
        self,
        path: str,
    ) -> list[SpeakerSegment]:
        """
        Run diarization on an audio file and return its segments.

        :param path: Path to the audio file.
        :raises RuntimeError: If called before load().
        :raises AudioError: If the file holds no decodable audio.
        :return: List of segments with start, end, and speaker fields.
        """
        if self.pipeline is None:
            raise RuntimeError("DiarizationPipeline.load() must be called before run()")
        audio = {"waveform": load_waveform(path), "sample_rate": _SAMPLE_RATE}
        output = self.pipeline(audio)
        return to_segments(output.exclusive_speaker_diarization)
