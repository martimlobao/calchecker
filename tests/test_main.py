from calchecker.__main__ import CALENDAR_STATE  # noqa: PLC2701


def test_filename() -> None:
    assert CALENDAR_STATE == "calendar.bin"
