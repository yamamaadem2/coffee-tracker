"""Unit tests for streak/popularity logic. No DB or API needed —
these test the pure functions in app/logic.py directly."""
from datetime import date, timedelta
from app.logic import calculate_streaks, most_popular_drinks

TODAY = date.today()


def days_ago(n):
    return TODAY - timedelta(days=n)


def test_no_orders_returns_zero_streaks():
    assert calculate_streaks([]) == (0, 0)


def test_single_order_today_is_streak_of_one():
    current, longest = calculate_streaks([TODAY])
    assert current == 1
    assert longest == 1


def test_consecutive_days_build_current_streak():
    dates = [days_ago(2), days_ago(1), TODAY]
    current, longest = calculate_streaks(dates)
    assert current == 3
    assert longest == 3


def test_broken_streak_resets_current_but_keeps_longest():
    # Orders 10 days ago for 4 days straight, then nothing recent
    dates = [days_ago(13), days_ago(12), days_ago(11), days_ago(10)]
    current, longest = calculate_streaks(dates)
    assert current == 0  # last order too long ago, streak is broken
    assert longest == 4


def test_yesterday_order_still_counts_as_active_streak():
    dates = [days_ago(2), days_ago(1)]
    current, longest = calculate_streaks(dates)
    assert current == 2

def test_duplicate_same_day_orders_count_once():
    dates = [TODAY, TODAY, TODAY]
    current, longest = calculate_streaks(dates)
    assert current == 1
    assert longest == 1


def test_most_popular_drinks_orders_by_count():
    drinks = ["Latte", "Latte", "Espresso", "Latte", "Mocha", "Espresso"]
    result = most_popular_drinks(drinks, top_n=2)
    assert result == [("Latte", 3), ("Espresso", 2)]


def test_most_popular_drinks_empty_list():
    assert most_popular_drinks([]) == []
