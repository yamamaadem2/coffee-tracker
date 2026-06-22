"""Business logic for computing order streaks and popular drinks.

Kept separate from the API layer so it's independently testable and
doesn't depend on FastAPI or the database session type.
"""
from datetime import date, timedelta
from collections import Counter


def calculate_streaks(order_dates: list[date]) -> tuple[int, int]:
    """Given a customer's order dates (any order, duplicates allowed),
    return (current_streak, longest_streak) in consecutive calendar days.

    A streak is a run of consecutive days with at least one order.
    "Current streak" counts backward from the most recent order date,
    and only counts as "active" if that most recent order was today
    or yesterday (otherwise the streak is considered broken).
    """
    if not order_dates:
        return 0, 0

    unique_days = sorted(set(order_dates))

    longest = 1
    current_run = 1
    for i in range(1, len(unique_days)):
        if unique_days[i] == unique_days[i - 1] + timedelta(days=1):
            current_run += 1
        else:
            current_run = 1
        longest = max(longest, current_run)

    # Determine current streak: walk backward from the last order day
    last_day = unique_days[-1]
    today = date.today()
    if last_day < today - timedelta(days=1):
        # Most recent order was before yesterday -> streak is broken
        return 0, longest

    streak = 1
    for i in range(len(unique_days) - 1, 0, -1):
        if unique_days[i] == unique_days[i - 1] + timedelta(days=1):
            streak += 1
        else:
            break

    return streak, longest


def most_popular_drinks(drinks: list[str], top_n: int = 5) -> list[tuple[str, int]]:
    """Return the top_n drinks by order count, descending."""
    counts = Counter(drinks)
    return counts.most_common(top_n)
