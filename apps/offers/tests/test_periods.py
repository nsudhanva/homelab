from datetime import date

from offers.periods import Period, window_for, windows_between


def test_monthly_window() -> None:
    w = window_for(Period.MONTHLY, date(2026, 12, 15))
    assert (w.start, w.end) == (date(2026, 12, 1), date(2027, 1, 1))
    assert w.days_left(date(2026, 12, 29)) == 3
    assert w.label == "Dec 2026"


def test_quarter_and_half_year() -> None:
    assert window_for(Period.QUARTERLY, date(2026, 5, 2)).start == date(2026, 4, 1)
    half = window_for(Period.SEMIANNUAL, date(2026, 7, 1))
    assert (half.start, half.end) == (date(2026, 7, 1), date(2027, 1, 1))


def test_cardmember_year_uses_anniversary() -> None:
    w = window_for(Period.CARDMEMBER_YEAR, date(2026, 2, 10), anniversary_month=3)
    assert (w.start, w.end) == (date(2025, 3, 1), date(2026, 3, 1))
    assert window_for(Period.CARDMEMBER_YEAR, date(2026, 2, 10)).start == date(2026, 1, 1)


def test_windows_between() -> None:
    windows = windows_between(Period.MONTHLY, date(2026, 1, 20), date(2026, 3, 1))
    assert [w.start.month for w in windows] == [1, 2, 3]


def test_once_window() -> None:
    w = window_for(Period.ONCE, date(2026, 5, 1), once_from=date(2026, 1, 1))
    assert w.start == date(2026, 1, 1) and w.contains(date(2029, 1, 1))
    assert w.label == "From Jan 2026"
    assert windows_between(Period.ONCE, date(2026, 1, 1), date(2027, 1, 1)) == [
        window_for(Period.ONCE, date(2026, 1, 1))
    ]
