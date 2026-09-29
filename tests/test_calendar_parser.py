"""
Unit tests for Core Calendar Parser Module
"""

import pytest
from datetime import date, datetime
from calendar_parser import CalendarParser, CalendarPeriod


class TestCalendarParser:

    @pytest.fixture
    def sample_periods(self):
        return [
            {
                "name": "Fall 2026 Semester",
                "period_type": "semester",
                "start_date": "2026-08-25",
                "end_date": "2026-12-15",
            },
            {
                "name": "Thanksgiving Break",
                "period_type": "break",
                "start_date": "2026-11-24",
                "end_date": "2026-11-28",
            },
            {
                "name": "Final Exams",
                "period_type": "exam_week",
                "start_date": "2026-12-08",
                "end_date": "2026-12-15",
            },
            {
                "name": "Winter Maintenance",
                "period_type": "maintenance",
                "start_date": "2026-12-20",
                "end_date": "2026-12-22",
            },
        ]

    @pytest.fixture
    def parser(self, sample_periods):
        return CalendarParser.from_dicts(sample_periods)

    def test_is_break_or_maintenance(self, parser):
        """Verify break and maintenance periods are accurately identified."""
        # Thanksgiving break
        assert parser.is_break_or_maintenance(date(2026, 11, 25)) is True
        # Winter maintenance
        assert parser.is_break_or_maintenance("2026-12-21") is True
        # Normal class day
        assert parser.is_break_or_maintenance(date(2026, 9, 15)) is False

    def test_is_exam_week(self, parser):
        """Verify exam week period classification."""
        assert parser.is_exam_week("2026-12-10") is True
        assert parser.is_exam_week("2026-10-10") is False

    def test_get_active_period(self, parser):
        """Verify active period lookup by date."""
        period = parser.get_active_period("2026-11-25")
        assert period is not None
        assert period.name == "Fall 2026 Semester" or period.name == "Thanksgiving Break"

    def test_is_course_semester_active(self, parser):
        """Verify course active date range checks."""
        start = "2026-08-25"
        end = "2026-12-15"

        assert parser.is_course_semester_active(start, end, "2026-10-01") is True
        assert parser.is_course_semester_active(start, end, "2027-01-10") is False

    def test_calculate_effective_grace_period(self, parser):
        """Verify grace period extended during break period."""
        # Start during break -> 72 hours base + 7 days (168 hours) = 240 hours
        break_dt = datetime(2026, 11, 25, 10, 0, 0)
        deadline_break = parser.calculate_effective_grace_period(72, break_dt, break_grace_days=7)
        assert (deadline_break - break_dt).total_seconds() == 240 * 3600

        # Start during normal day -> 72 hours
        normal_dt = datetime(2026, 9, 15, 10, 0, 0)
        deadline_normal = parser.calculate_effective_grace_period(72, normal_dt, break_grace_days=7)
        assert (deadline_normal - normal_dt).total_seconds() == 72 * 3600
