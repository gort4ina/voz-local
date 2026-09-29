from copy import deepcopy


class SegmentMergeService:
    def merge(self, segments, turns=(), max_gap=0.6, max_duration=30.0):
        result = []
        for original in sorted(segments, key=lambda s: s.start):
            current = deepcopy(original)
            previous = result[-1] if result else None
            interrupted = previous and any(
                t.speaker != previous.speaker and t.start < current.start and t.end > previous.end
                for t in turns
            )
            can_merge = (
                previous
                and current.speaker == previous.speaker
                and current.candidates == previous.candidates
                and current.overlap == previous.overlap
                and current.needs_review == previous.needs_review
                and 0 <= current.start - previous.end <= max_gap
                and current.end - previous.start <= max_duration
                and not interrupted
            )
            if can_merge:
                previous.end = current.end
                previous.text += (
                    current.text if current.text.startswith(" ") else " " + current.text
                )
                previous.words.extend(current.words)
                values = [
                    w["confidence"] for w in previous.words if w.get("confidence") is not None
                ]
                previous.confidence = sum(values) / len(values) if values else None
            else:
                result.append(current)
        for segment in result:
            segment.text = segment.text.strip()
        return result
