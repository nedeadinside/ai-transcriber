import logging
from typing import TYPE_CHECKING, Final

from api.schemas import Segment

if TYPE_CHECKING:
    from clients.whisper import AsrSegment
    from core.api.schemas import SpeakerSegment

logger = logging.getLogger(__name__)

_TIMESTAMP_NDIGITS: Final[int] = 3


def _overlap(start: float, end: float, other_start: float, other_end: float) -> float:
    """
    Return the length of the intersection between two intervals.

    :param start: Start of the first interval.
    :param end: End of the first interval.
    :param other_start: Start of the second interval.
    :param other_end: End of the second interval.
    :return: Overlap in seconds, zero when the intervals are disjoint.
    """
    return max(0.0, min(end, other_end) - max(start, other_start))


def _speaker_at(start: float, end: float, speaker_segments: list["SpeakerSegment"]) -> str | None:
    """
    Return the speaker whose segment overlaps the interval the most.

    :param start: Start of the interval.
    :param end: End of the interval.
    :param speaker_segments: Diarization segments to match against.
    :return: Speaker label, or None when nothing overlaps.
    """
    best: str | None = None
    best_overlap = 0.0
    for seg in speaker_segments:
        overlap = _overlap(start, end, seg.start, seg.end)
        if overlap > best_overlap:
            best_overlap = overlap
            best = seg.speaker
    if best is None and end <= start:
        for seg in speaker_segments:
            if seg.start <= start <= seg.end:
                return seg.speaker
    return best


def attach_speakers(
    segments: list["AsrSegment"], speaker_segments: list["SpeakerSegment"]
) -> list[Segment]:
    """
    Attach speaker labels to transcript segments, splitting them at speaker turns.

    :param segments: Transcript segments from the ASR service.
    :param speaker_segments: Diarization segments.
    :return: Segments carrying a speaker label, split at speaker turns.
    """
    if not speaker_segments:
        return [
            Segment(
                start=round(seg.start, _TIMESTAMP_NDIGITS),
                end=round(seg.end, _TIMESTAMP_NDIGITS),
                text=seg.text.strip(),
                speaker=None,
            )
            for seg in segments
        ]
    out: list[Segment] = []
    for seg in segments:
        if not seg.words:
            logger.warning(
                "no word timestamps for segment %.2f-%.2f, falling back to segment-level "
                "speaker matching; check ASR_ENGINE=faster_whisper",
                seg.start,
                seg.end,
            )
            out.append(
                Segment(
                    start=round(seg.start, _TIMESTAMP_NDIGITS),
                    end=round(seg.end, _TIMESTAMP_NDIGITS),
                    text=seg.text.strip(),
                    speaker=_speaker_at(seg.start, seg.end, speaker_segments),
                )
            )
            continue

        for word in seg.words:
            speaker = _speaker_at(word.start, word.end, speaker_segments)
            start = round(word.start, _TIMESTAMP_NDIGITS)
            end = round(word.end, _TIMESTAMP_NDIGITS)
            if out and out[-1].speaker == speaker and out[-1].end <= start:
                out[-1].end = end
                out[-1].text += word.word
            else:
                out.append(
                    Segment(
                        start=start,
                        end=end,
                        text=word.word,
                        speaker=speaker,
                    )
                )

    for seg_out in out:
        seg_out.text = seg_out.text.strip()
    return out
