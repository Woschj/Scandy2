import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.utils.date_utils import (
    format_datetime,
    format_date,
    format_time,
    format_datetime_full,
    parse_datetime,
    format_relative_date,
    format_duration,
    is_workday,
    get_next_workday,
    get_week_dates,
    format_datetime_for_database,
    parse_datetime_from_database,
    get_current_week,
    format_week_range
)

# Custom datetime mocks to preserve isinstance and strptime
class MockDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2024, 4, 15, 12, 0, 0)

class MockDatetimeThursday(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2024, 4, 18, 12, 0, 0)

def test_format_datetime():
    dt = datetime(2024, 4, 15, 14, 30, 45)
    assert format_datetime(dt) == "15.04.2024 14:30"

    # Test string parsing
    assert format_datetime("2024-04-15 14:30:45") == "15.04.2024 14:30"
    assert format_datetime("15.04.2024 14:30") == "15.04.2024 14:30"

    # Test invalid string - the current implementation throws an AttributeError
    # if it cannot parse the string but still tries to call strftime.
    with pytest.raises(AttributeError):
        format_datetime("invalid-date")

    # Test None
    assert format_datetime(None) == ""

def test_format_date():
    dt = datetime(2024, 4, 15, 14, 30, 45)
    assert format_date(dt) == "15.04.2024"
    assert format_date(None) == ""

def test_format_time():
    dt = datetime(2024, 4, 15, 14, 30, 45)
    assert format_time(dt) == "14:30"
    assert format_time(None) == ""

def test_format_datetime_full():
    dt = datetime(2024, 4, 15, 14, 30, 45)
    assert format_datetime_full(dt) == "15.04.2024 14:30:45"
    assert format_datetime_full(None) == ""

def test_parse_datetime():
    dt = parse_datetime("15.04.2024 14:30")
    assert isinstance(dt, datetime)
    assert dt.year == 2024
    assert dt.month == 4
    assert dt.day == 15
    assert dt.hour == 14
    assert dt.minute == 30

    # Test invalid and None
    assert parse_datetime(None) is None
    assert parse_datetime("invalid-date") is None

@patch('app.utils.date_utils.datetime', new=MockDatetime)
def test_format_relative_date():
    # 1. Heute
    dt_heute = datetime(2024, 4, 15, 14, 30, 0)
    assert format_relative_date(dt_heute) == "Heute, 14:30"

    # 2. Gestern
    dt_gestern = datetime(2024, 4, 14, 9, 15, 0)
    assert format_relative_date(dt_gestern) == "Gestern, 09:15"

    # 3. Morgen
    dt_morgen = datetime(2024, 4, 16, 18, 45, 0)
    assert format_relative_date(dt_morgen) == "Morgen, 18:45"

    # 4. Other dates
    dt_other = datetime(2024, 4, 10, 10, 0, 0)
    assert format_relative_date(dt_other) == "10.04.2024 10:00"

    # 5. String parsing
    assert format_relative_date("15.04.2024 14:30") == "Heute, 14:30"
    assert format_relative_date("10.04.2024 10:00") == "10.04.2024 10:00"

    # 6. Edge cases
    assert format_relative_date(None) == ""
    # Invalid string parse_datetime returns None, the function might return None
    assert format_relative_date("invalid-date") is None

def test_format_duration():
    # 0 minutes or None
    assert format_duration(None) == '0 Minuten'
    assert format_duration(timedelta(seconds=0)) == '0 Minuten'
    assert format_duration(timedelta(seconds=30)) == 'Weniger als 1 Minute'

    # Minutes
    assert format_duration(timedelta(minutes=1)) == '1 Minute'
    assert format_duration(timedelta(minutes=45)) == '45 Minuten'

    # Hours
    assert format_duration(timedelta(hours=1)) == '1 Stunde'
    assert format_duration(timedelta(hours=2)) == '2 Stunden'

    # Hours and minutes
    assert format_duration(timedelta(hours=1, minutes=30)) == '1 Stunde 30 Minuten'

    # Days
    assert format_duration(timedelta(days=1)) == '1 Tag'
    assert format_duration(timedelta(days=3)) == '3 Tage'

    # Days and hours (minutes are not shown if days > 0)
    assert format_duration(timedelta(days=1, hours=2, minutes=30)) == '1 Tag 2 Stunden'

def test_is_workday():
    # Monday to Friday
    assert is_workday(datetime(2024, 4, 15)) is True  # Monday
    assert is_workday(datetime(2024, 4, 19)) is True  # Friday

    # Weekend
    assert is_workday(datetime(2024, 4, 20)) is False # Saturday
    assert is_workday(datetime(2024, 4, 21)) is False # Sunday

@patch('app.utils.date_utils.datetime', new=MockDatetimeThursday)
def test_get_next_workday():
    # Next day is Friday (workday)
    thursday = datetime(2024, 4, 18)
    assert get_next_workday(thursday).date() == datetime(2024, 4, 19).date()

    # Next day from Friday is Monday
    friday = datetime(2024, 4, 19)
    assert get_next_workday(friday).date() == datetime(2024, 4, 22).date()

    # Next day from Saturday is Monday
    saturday = datetime(2024, 4, 20)
    assert get_next_workday(saturday).date() == datetime(2024, 4, 22).date()

    # If date is None, uses datetime.now()
    # Which is mocked to Thursday, so next workday is Friday
    assert get_next_workday(None).date() == datetime(2024, 4, 19).date()

def test_get_week_dates():
    dates = get_week_dates(2024, 16) # Week of April 15, 2024
    assert len(dates) == 5

    assert dates[0]['date'].date() == datetime(2024, 4, 15).date()
    assert dates[0]['formatted'] == '15.04.2024'
    assert dates[0]['day_name'] == 'Montag'

    assert dates[4]['date'].date() == datetime(2024, 4, 19).date()
    assert dates[4]['formatted'] == '19.04.2024'
    assert dates[4]['day_name'] == 'Freitag'

def test_format_datetime_for_database():
    dt = datetime(2024, 4, 15, 14, 30, 45)
    assert format_datetime_for_database(dt) == '2024-04-15 14:30:45'
    assert format_datetime_for_database(None) is None

def test_parse_datetime_from_database():
    dt = parse_datetime_from_database('2024-04-15 14:30:45')
    assert isinstance(dt, datetime)
    assert dt.year == 2024
    assert dt.month == 4
    assert dt.day == 15
    assert dt.hour == 14
    assert dt.minute == 30
    assert dt.second == 45

    assert parse_datetime_from_database(None) is None
    assert parse_datetime_from_database('invalid-date') is None

@patch('app.utils.date_utils.datetime', new=MockDatetime)
def test_get_current_week():
    # April 15, 2024 is week 16
    assert get_current_week() == (2024, 16)

def test_format_week_range():
    # Week 16 of 2024 is April 15 to April 19
    assert format_week_range(2024, 16) == "15.04.2024 - 19.04.2024"
