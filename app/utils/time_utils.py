from datetime import datetime, timedelta

"""
Time Utilities - v2.8.2

Utility functions for time and date manipulation.
"""



def parse_relative_timeframe(timeframe: str) -> tuple[datetime, datetime]:
    """
    Parse relative timeframe string into start and end dates.

    Args:
        timeframe: Relative timeframe like 'last_7_days', 'this_month', etc.

    Returns:
        Tuple of (start_date, end_date)
    """
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if timeframe == "last_24_hours":
        return now - timedelta(hours=24), now

    elif timeframe == "last_7_days":
        return today - timedelta(days=7), now

    elif timeframe == "last_30_days":
        return today - timedelta(days=30), now

    elif timeframe == "last_month":
        # First day of last month
        if today.month == 1:
            start = today.replace(year=today.year - 1, month=12, day=1)
        else:
            start = today.replace(month=today.month - 1, day=1)

        # Last day of last month
        end = today.replace(day=1) - timedelta(days=1)
        end = end.replace(hour=23, minute=59, second=59)

        return start, end

    elif timeframe == "last_quarter":
        # Determine current quarter
        quarter = (today.month - 1) // 3

        # Calculate last quarter
        if quarter == 0:
            # Last quarter of previous year
            start = today.replace(year=today.year - 1, month=10, day=1)
            end = today.replace(year=today.year - 1, month=12, day=31)
        else:
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            start = today.replace(month=start_month, day=1)

            # Last day of end month
            if end_month == 12:
                end = today.replace(month=12, day=31)
            else:
                end = today.replace(month=end_month + 1, day=1) - timedelta(days=1)

        end = end.replace(hour=23, minute=59, second=59)
        return start, end

    elif timeframe == "last_year":
        start = today.replace(year=today.year - 1, month=1, day=1)
        end = today.replace(year=today.year - 1, month=12, day=31, hour=23, minute=59, second=59)
        return start, end

    elif timeframe == "this_week":
        # Start of week (Monday)
        start = today - timedelta(days=today.weekday())
        return start, now

    elif timeframe == "this_month":
        start = today.replace(day=1)
        return start, now

    elif timeframe == "this_quarter":
        quarter = (today.month - 1) // 3
        start_month = quarter * 3 + 1
        start = today.replace(month=start_month, day=1)
        return start, now

    elif timeframe == "this_year":
        start = today.replace(month=1, day=1)
        return start, now

    else:
        # Default to last 30 days
        return today - timedelta(days=30), now


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "2h 15m" or "45s"
    """
    if seconds < 60:
        return f"{seconds}s"

    minutes = seconds // 60
    seconds = seconds % 60

    if minutes < 60:
        return f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes}m"

    hours = minutes // 60
    minutes = minutes % 60

    if hours < 24:
        parts = [f"{hours}h"]
        if minutes > 0:
            parts.append(f"{minutes}m")
        return " ".join(parts)

    days = hours // 24
    hours = hours % 24

    parts = [f"{days}d"]
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")

    return " ".join(parts)


def calculate_time_ago(timestamp: datetime) -> str:
    """
    Calculate how long ago a timestamp was.

    Args:
        timestamp: Past datetime

    Returns:
        Human-readable string like "2 hours ago" or "3 days ago"
    """
    now = datetime.utcnow()
    diff = now - timestamp

    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "just now"

    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"

    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

    days = hours // 24
    if days < 7:
        return f"{days} day{'s' if days != 1 else ''} ago"

    weeks = days // 7
    if weeks < 4:
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"

    months = days // 30
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''} ago"

    years = days // 365
    return f"{years} year{'s' if years != 1 else ''} ago"
