"""Benefit periods. Each period is a half-open date range [start, end)."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class Period(StrEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    ANNUAL = "annual"
    CARDMEMBER_YEAR = "cardmember_year"
    ONCE = "once"


ONCE_END = date(9999, 1, 1)


@dataclass(frozen=True, order=True)
class Window:
    start: date
    end: date

    def contains(self, day: date) -> bool:
        return self.start <= day < self.end

    def days_left(self, today: date) -> int:
        return max((self.end - today).days, 0)

    @property
    def label(self) -> str:
        if self.end == ONCE_END:
            return f"From {self.start.strftime('%b %Y')}"
        last = date.fromordinal(self.end.toordinal() - 1)
        if (self.start.year, self.start.month) == (last.year, last.month):
            return self.start.strftime("%b %Y")
        return f"{self.start.strftime('%b %Y')} - {last.strftime('%b %Y')}"


def _add_months(day: date, months: int) -> date:
    index = day.year * 12 + (day.month - 1) + months
    return date(index // 12, index % 12 + 1, 1)


def window_for(
    period: Period,
    day: date,
    anniversary_month: int | None = None,
    once_from: date | None = None,
) -> Window:
    """Return the period window that contains ``day``.

    A card-member year starts in ``anniversary_month``. Without a known anniversary month,
    it is the calendar year.
    """
    if period is Period.ONCE:
        return Window(once_from or date(day.year, 1, 1), ONCE_END)
    if period is Period.MONTHLY:
        start = date(day.year, day.month, 1)
        return Window(start, _add_months(start, 1))
    if period is Period.QUARTERLY:
        start = date(day.year, (day.month - 1) // 3 * 3 + 1, 1)
        return Window(start, _add_months(start, 3))
    if period is Period.SEMIANNUAL:
        start = date(day.year, 1 if day.month <= 6 else 7, 1)
        return Window(start, _add_months(start, 6))
    if period is Period.ANNUAL or anniversary_month is None:
        return Window(date(day.year, 1, 1), date(day.year + 1, 1, 1))
    year = day.year if day.month >= anniversary_month else day.year - 1
    start = date(year, anniversary_month, 1)
    return Window(start, _add_months(start, 12))


def windows_between(
    period: Period, first: date, last: date, anniversary_month: int | None = None
) -> list[Window]:
    """Return every window that overlaps the inclusive range ``first`` to ``last``."""
    if period is Period.ONCE:
        return [window_for(period, first)]
    windows: list[Window] = []
    current = window_for(period, first, anniversary_month)
    while current.start <= last:
        windows.append(current)
        current = window_for(period, current.end, anniversary_month)
    return windows
