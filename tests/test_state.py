import json
from src.state import SyncState


def test_mark_and_check(tmp_path):
    state = SyncState(str(tmp_path))
    assert not state.is_synced("2026-03-28")

    state.mark_synced("2026-03-28")
    assert state.is_synced("2026-03-28")
    assert not state.is_synced("2026-03-27")


def test_last_synced(tmp_path):
    state = SyncState(str(tmp_path))
    assert state.last_synced() is None

    state.mark_synced("2026-03-26")
    state.mark_synced("2026-03-28")
    state.mark_synced("2026-03-27")
    assert state.last_synced() == "2026-03-28"


def test_persistence(tmp_path):
    state1 = SyncState(str(tmp_path))
    state1.mark_synced("2026-03-28")

    # New instance should load from disk
    state2 = SyncState(str(tmp_path))
    assert state2.is_synced("2026-03-28")


def test_corrupt_file(tmp_path):
    state_file = tmp_path / "sync_state.json"
    state_file.write_text("not valid json {{{")

    state = SyncState(str(tmp_path))
    assert state.last_synced() is None
    # Should still work after corrupt load
    state.mark_synced("2026-03-28")
    assert state.is_synced("2026-03-28")
