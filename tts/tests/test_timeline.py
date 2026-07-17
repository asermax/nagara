from app import build_timeline


def _total(durations, pause_s):
    return sum(durations) + pause_s * (len(durations) - 1)


def test_windows_are_contiguous_and_monotonic():
    durations = [3.0, 5.0, 2.0]
    tl = build_timeline(durations, 0.75)

    assert [e["index"] for e in tl] == [0, 1, 2]
    assert tl[0]["start"] == 0.0
    for prev, nxt in zip(tl, tl[1:]):
        assert nxt["start"] == prev["end"]  # contiguous
        assert nxt["end"] > nxt["start"]  # monotonic, non-overlapping


def test_last_end_equals_total_audio_duration():
    durations = [3.0, 5.0, 2.0]
    tl = build_timeline(durations, 0.75)
    assert tl[-1]["end"] == _total(durations, 0.75)


def test_pause_folded_into_preceding_window():
    tl = build_timeline([3.0, 5.0], 0.75)
    assert tl[0]["end"] == 3.0 + 0.75  # first window carries the pause
    assert tl[1]["end"] == 3.0 + 0.75 + 5.0  # last carries none


def test_single_paragraph_has_no_pause():
    tl = build_timeline([4.0], 0.75)
    assert tl == [{"index": 0, "start": 0.0, "end": 4.0}]


def test_empty_is_empty():
    assert build_timeline([], 0.75) == []
