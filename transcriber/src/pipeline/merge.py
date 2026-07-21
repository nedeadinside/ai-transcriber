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


def _speaker_at(
    start: float,
    end: float,
    speaker_segments: list["SpeakerSegment"],
    cursor: int,
) -> tuple[str | None, int]:
    """
    Return the speaker whose segment overlaps the interval the most, plus the advanced cursor.

    Two-pointer scan over sorted, non-overlapping segments (exclusive_speaker_diarization).
    Callers must query in non-decreasing ``start`` order and thread the returned cursor back
    in: once a segment ends before the current start it cannot match any later query, so the
    cursor only moves forward and the whole pass is O(M + N) instead of O(M * N).

    :param start: Start of the interval.
    :param end: End of the interval.
    :param speaker_segments: Diarization segments, sorted by start and non-overlapping.
    :param cursor: Index to start scanning from, from a previous call.
    :return: Best-matching speaker label (or None), and the new cursor.
    """
    while cursor < len(speaker_segments) and speaker_segments[cursor].end < start:
        cursor += 1

    best: str | None = None
    best_overlap = 0.0
    j = cursor
    while j < len(speaker_segments) and speaker_segments[j].start < end:
        seg = speaker_segments[j]
        overlap = _overlap(start, end, seg.start, seg.end)
        if overlap > best_overlap:
            best_overlap = overlap
            best = seg.speaker
        j += 1

    if best is None and end <= start and cursor < len(speaker_segments):
        seg = speaker_segments[cursor]
        if seg.start <= start <= seg.end:
            best = seg.speaker
    return best, cursor


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
    cursor = 0
    for seg in segments:
        if not seg.words:
            logger.warning(
                "no word timestamps for segment %.2f-%.2f, falling back to segment-level "
                "speaker matching; check ASR_ENGINE=faster_whisper",
                seg.start,
                seg.end,
            )
            speaker, cursor = _speaker_at(seg.start, seg.end, speaker_segments, cursor)
            out.append(
                Segment(
                    start=round(seg.start, _TIMESTAMP_NDIGITS),
                    end=round(seg.end, _TIMESTAMP_NDIGITS),
                    text=seg.text.strip(),
                    speaker=speaker,
                )
            )
            continue

        for word in seg.words:
            speaker, cursor = _speaker_at(word.start, word.end, speaker_segments, cursor)
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
