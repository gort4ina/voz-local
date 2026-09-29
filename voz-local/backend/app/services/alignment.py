import math
from dataclasses import asdict

from app.schemas.domain import AlignedSegment


def union_duration(intervals):
    total, end = 0.0, float("-inf")
    for start, stop in sorted(intervals):
        total += max(0.0, stop - max(start, end))
        end = max(end, stop)
    return total


class SegmentAlignmentService:
    def align(self, words, turns):
        """Sweep words against regular diarization; never alternate speakers by index.

        Scores are intersection durations, unioned per speaker to avoid double counting.
        A tie is unknown. Concurrent candidates are retained without duplicating ASR text.
        """
        turns = sorted((t for t in turns if t.end > t.start), key=lambda t: t.start)
        active, cursor, output = [], 0, []
        for w in sorted(words, key=lambda w: w.start):
            if (
                not (math.isfinite(w.start) and math.isfinite(w.end))
                or w.start < 0
                or w.end <= w.start
                or not w.word.strip()
            ):
                continue
            while cursor < len(turns) and turns[cursor].start < w.end:
                active.append(turns[cursor])
                cursor += 1
            active = [t for t in active if t.end > w.start]
            intervals = {}
            for t in active:
                start, end = max(w.start, t.start), min(w.end, t.end)
                if end > start:
                    intervals.setdefault(t.speaker, []).append((start, end))
            scores = {s: union_duration(parts) for s, parts in intervals.items()}
            ranked = sorted(scores, key=lambda s: (-scores[s], s))
            tied = len(ranked) > 1 and abs(scores[ranked[0]] - scores[ranked[1]]) < 1e-6
            label = ranked[0] if ranked and not tied else "UNKNOWN"
            overlap = any(
                max(a, c) < min(b, d)
                for i, s in enumerate(ranked)
                for other in ranked[i + 1 :]
                for a, b in intervals[s]
                for c, d in intervals[other]
            )
            coverage = scores.get(label, 0) / (w.end - w.start)
            review = label == "UNKNOWN" or len(ranked) > 1 or coverage < 0.5
            word = {**asdict(w), "speaker": label, "candidate_labels": ranked}
            output.append(
                AlignedSegment(
                    w.start, w.end, w.word, label, w.confidence, [word], ranked, overlap, review
                )
            )
        return output
