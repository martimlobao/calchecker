from calchecker.__main__ import STATE_FILE


def test_filename() -> None:
    assert STATE_FILE == "state.bin"
