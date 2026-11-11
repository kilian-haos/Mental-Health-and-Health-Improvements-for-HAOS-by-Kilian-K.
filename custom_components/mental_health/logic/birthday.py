"""Birthdays (pure Python): age, next birthday, several people on the same day, no year, 29 Feb."""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Birthdate:
    month: int
    day: int
    year: int | None = None        # ohne Jahr: kein Alter

    @classmethod
    def parse(cls, value: str | None) -> Birthdate | None:
        """'YYYY-MM-DD' or '--MM-DD' / 'MM-DD' (no year)."""
        s = str(value or "").strip()
        if not s:
            return None
        try:
            if s.startswith("--"):
                s = s[2:]
            parts = [int(p) for p in s.split("-")]
            if len(parts) == 3:
                y, m, d = parts
                date(y, m, d)
                return cls(m, d, y)
            if len(parts) == 2:
                m, d = parts
                date(2000, m, d)   # Schaltjahr, damit 02-29 gültig ist
                return cls(m, d, None)
        except (ValueError, TypeError):
            return None
        return None

    def to_str(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}" if self.year else f"--{self.month:02d}-{self.day:02d}"

    def occurrence(self, year: int) -> date:
        """Birthday in a given year; 29 Feb falls on 28 Feb in non-leap years."""
        if self.month == 2 and self.day == 29 and not calendar.isleap(year):
            return date(year, 2, 28)
        return date(year, self.month, self.day)

    def age(self, today: date) -> int | None:
        if self.year is None:
            return None
        occ = self.occurrence(today.year)
        return today.year - self.year - (1 if today < occ else 0)

    def next_birthday(self, today: date) -> date:
        occ = self.occurrence(today.year)
        return occ if occ >= today else self.occurrence(today.year + 1)

    def is_today(self, today: date) -> bool:
        return self.occurrence(today.year) == today

    def days_until(self, today: date) -> int:
        return (self.next_birthday(today) - today).days

    def turning(self, today: date) -> int | None:
        """Age on the next birthday."""
        if self.year is None:
            return None
        return self.next_birthday(today).year - self.year


def family_today(people: dict[str, Birthdate | None], today: date) -> list[str]:
    return sorted(pid for pid, b in people.items() if b is not None and b.is_today(today))


def family_next(people: dict[str, Birthdate | None], today: date, include_today: bool = False) -> tuple[date | None, list[str]]:
    """Next birthday date in the family and everyone who has it on that day."""
    best: date | None = None
    who: list[str] = []
    for pid, b in people.items():
        if b is None:
            continue
        nb = b.next_birthday(today)
        if nb == today and not include_today:
            nb = b.occurrence(today.year + 1)
        if best is None or nb < best:
            best, who = nb, [pid]
        elif nb == best:
            who.append(pid)
    return best, sorted(who)


def age_from(value: str | None, today: date) -> int | None:
    b = Birthdate.parse(value)
    return b.age(today) if b else None
