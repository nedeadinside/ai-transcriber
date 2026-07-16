import logging
from typing import TYPE_CHECKING, Final, TypedDict

if TYPE_CHECKING:
    from pyannote.audio import Pipeline
    from pyannote.core import Annotation

    from config.models import AppConfig

logger = logging.getLogger(__name__)

_TIMESTAMP_NDIGITS: Final[int] = 3


class SegmentDict(TypedDict):
    """
    A single speech segment for one speaker.
    """

    start: float
    end: float
    speaker: str


def to_segments(annotation: "Annotation") -> list[SegmentDict]:
    """
    Convert a diarization result into a list of segments.

    :param annotation: Result produced by the pipeline.
    :return: List of segments with start, end, and speaker fields.
    """
    return [
        {
            "start": round(segment.start, _TIMESTAMP_NDIGITS),
            "end": round(segment.end, _TIMESTAMP_NDIGITS),
            "speaker": speaker,
        }
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
            use_auth_token=self.cfg.model.auth_token,
        )
        self.pipeline.to(self.device)
        logger.info("pyannote pipeline loaded on device: %s", self.device)

    def run(
        self,
        path: str,
    ) -> list[SegmentDict]:
        """
        Run diarization on an audio file and return its segments.

        :param path: Path to the audio file.
        :raises RuntimeError: If called before load().
        :return: List of segments with start, end, and speaker fields.
        """
        if self.pipeline is None:
            raise RuntimeError("DiarizationPipeline.load() must be called before run()")
        annotation = self.pipeline(path)
        return to_segments(annotation)
