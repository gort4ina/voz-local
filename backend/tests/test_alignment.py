import pytest

from app.schemas.domain import AlignedSegment, Turn, Word
from app.services.alignment import SegmentAlignmentService
from app.services.merge import SegmentMergeService


def align(words, turns):
    return SegmentAlignmentService().align(words, turns)


def test_overlap_duration_assigns_words_not_alternating_indexes():
    result = align(
        [Word(0, 1, "Olá"), Word(1, 2, " tudo bem"), Word(3, 4, " sim")],
        [Turn(0, 2.5, "A"), Turn(2.5, 4, "B")],
    )
    assert [s.speaker for s in result] == ["A", "A", "B"]


def test_boundary_splits_an_asr_sentence_at_word_level():
    result = align(
        [Word(0, 1, "Pergunta"), Word(1, 2, "Resposta")], [Turn(0, 1, "A"), Turn(1, 2, "B")]
    )
    assert [s.speaker for s in result] == ["A", "B"]


def test_tie_is_unknown_and_keeps_overlapping_speaker_candidates():
    result = align([Word(1, 2, "sim")], [Turn(0, 3, "A"), Turn(1, 2, "B")])[0]
    assert result.speaker == "UNKNOWN"
    assert result.candidates == ["A", "B"]
    assert result.overlap and result.needs_review


def test_boundary_without_simultaneous_speech_is_not_overlap():
    result = align([Word(0.8, 1.2, "sim")], [Turn(0, 1, "A"), Turn(1, 2, "B")])[0]
    assert not result.overlap and result.needs_review


def test_no_temporal_match_does_not_invent_a_speaker():
    result = align([Word(10, 11, "oi")], [Turn(0, 1, "A")])[0]
    assert result.speaker == "UNKNOWN" and result.needs_review


def test_duplicate_tracks_for_same_speaker_do_not_double_score():
    result = align([Word(0, 2, "oi")], [Turn(0, 1, "A"), Turn(0, 1, "A"), Turn(0, 1.5, "B")])[0]
    assert result.speaker == "B"


def test_original_word_timing_and_confidence_preserved():
    result = align([Word(1.12, 1.95, " dormir", 0.87)], [Turn(0, 2, "A")])[0]
    assert result.words[0]["start"] == 1.12
    assert result.words[0]["end"] == 1.95
    assert result.confidence == 0.87


@pytest.mark.parametrize(
    "word", [Word(-1, 2, "bad"), Word(1, 1, "bad"), Word(float("nan"), 2, "bad"), Word(1, 2, " ")]
)
def test_invalid_word_intervals_rejected(word):
    assert align([word], []) == []


def test_merge_consecutive_speaker_words_and_confidence():
    words = [Word(0, 1, "Bom", 0.9), Word(1, 2, " dia.", 0.7)]
    result = SegmentMergeService().merge(align(words, [Turn(0, 2, "A")]))
    assert len(result) == 1 and result[0].text == "Bom dia."
    assert result[0].confidence == pytest.approx(0.8)
    assert len(result[0].words) == 2


def test_merge_preserves_long_gaps_speaker_changes_and_overlap():
    items = [
        AlignedSegment(0, 1, "um", "A"),
        AlignedSegment(3, 4, "dois", "A"),
        AlignedSegment(4, 5, "três", "B"),
        AlignedSegment(4.5, 6, "quatro", "B"),
    ]
    assert len(SegmentMergeService().merge(items)) == 4


def test_untranscribed_interruption_prevents_merge():
    items = [AlignedSegment(0, 1, "um", "A"), AlignedSegment(1.5, 2, "dois", "A")]
    assert len(SegmentMergeService().merge(items, [Turn(1.1, 1.3, "B")])) == 2


def test_maximum_merge_duration():
    items = [AlignedSegment(0, 20, "um", "A"), AlignedSegment(20, 31, "dois", "A")]
    assert len(SegmentMergeService().merge(items)) == 2
