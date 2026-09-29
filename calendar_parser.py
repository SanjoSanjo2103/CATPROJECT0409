"""
CloudReclaim — Core Calendar Parser Module
Parses university academic calendars, semester schedules, break periods, exam weeks, and maintenance windows.
"""

from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional


@dataclass
class CalendarPeriod:
    """Dataclass for a single academic calendar period."""
    name: str
    period_type: str  # 'semester', 'break', 'exam_week', 'maintenance'
    start_date: date
    end_date: date

    def is_date_within(self, target_date: date) -> bool:
        return self.start_date <= target_date <= self.end_date


class CalendarParser:
    """
    Parser and date classifier for academic calendars and course semester schedules.
    """

    def __init__(self, periods: Optional[List[CalendarPeriod]] = None):
        self.periods = periods if periods is not None else []

    @classmethod
    def from_dicts(cls, period_dicts: List[Dict[str, Any]]) -> "CalendarParser":
        """Instantiate parser from a list of period dictionaries."""
        parsed_periods = []
        for p in period_dicts:
            start_d = cls._parse_date(p["start_date"])
            end_d = cls._parse_date(p["end_date"])
            parsed_periods.append(
                CalendarPeriod(
                    name=p["name"],
                    period_type=p["period_type"],
                    start_date=start_d,
                    end_date=end_d,
                )
            )
        return cls(parsed_periods)

    @staticmethod
    def _parse_date(val: Any) -> date:
        if isinstance(val, date) and not isinstance(val, datetime):
            return val
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, str):
            return datetime.strptime(val[:10], "%Y-%m-%d").date()
        raise ValueError(f"Cannot parse date: {val}")

    def is_break_or_maintenance(self, target_date: Any) -> bool:
        """Check if target_date falls within a break or maintenance period."""
        d = self._parse_date(target_date)
        return any(
            p.period_type in ("break", "maintenance") and p.is_date_within(d)
            for p in self.periods
        )

    def is_exam_week(self, target_date: Any) -> bool:
        """Check if target_date falls within an exam week period."""
        d = self._parse_date(target_date)
        return any(
            p.period_type == "exam_week" and p.is_date_within(d)
            for p in self.periods
        )

    def get_active_period(self, target_date: Any) -> Optional[CalendarPeriod]:
        """Return the matching CalendarPeriod for target_date if any."""
        d = self._parse_date(target_date)
        for p in self.periods:
            if p.is_date_within(d):
                return p
        return None

    def is_course_semester_active(self, course_start: Any, course_end: Any, target_date: Any) -> bool:
        """Check if course is within active start and end dates."""
        t_date = self._parse_date(target_date)
        s_date = self._parse_date(course_start)
        e_date = self._parse_date(course_end)
        return s_date <= t_date <= e_date

    def calculate_effective_grace_period(
        self,
        base_grace_hours: int,
        start_timestamp: datetime,
        break_grace_days: int = 7,
    ) -> datetime:
        """
        Calculate reclamation grace period deadline, extending by break_grace_days if starting during a break.
        """
        grace_hours = base_grace_hours
        if self.is_break_or_maintenance(start_timestamp):
            grace_hours += break_grace_days * 24

        return start_timestamp + timedelta(hours=grace_hours)
