from calchecker.__main__ import CALENDAR_STATE


def test_filename() -> None:
    assert CALENDAR_STATE == "calendar.bin"
