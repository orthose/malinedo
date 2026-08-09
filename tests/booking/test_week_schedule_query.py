import datetime
import pytest

from accounts.models import User
from booking.models import GlobalState, SessionRegistration, WeeklySession
from booking.query import WeekScheduleQuery


@pytest.fixture
def data(db) -> dict:
    # Given
    current_year = 2026
    current_week = 30
    GlobalState.set_year(current_year)
    GlobalState.set_week(current_week)

    alice_swimmer = User.objects.create_user(
        username="alice@example.com",
        email="alice@example.com",
        first_name="Alice",
        last_name="Dupont",
        password="secret",
    )
    bob_swimmer = User.objects.create_user(
        username="bob@example.com",
        email="bob@example.com",
        first_name="Bob",
        last_name="Martin",
        password="secret",
    )

    past_session = WeeklySession.objects.create(
        year=current_year,
        week=current_week - 1,
        weekday=2,
        start_hour=datetime.time(20, 30),
        stop_hour=datetime.time(21, 30),
        capacity=8,
    )
    current_session = WeeklySession.objects.create(
        year=current_year,
        week=current_week,
        weekday=2,
        start_hour=datetime.time(20, 30),
        stop_hour=datetime.time(21, 30),
        capacity=10,
    )
    future_session = WeeklySession.objects.create(
        year=current_year,
        week=current_week + 1,
        weekday=2,
        start_hour=datetime.time(20, 30),
        stop_hour=datetime.time(21, 30),
        capacity=12,
    )

    alice_registration = SessionRegistration.objects.create(
        swimmer=alice_swimmer,
        session=current_session,
        is_regular=True,
    )
    bob_registration = SessionRegistration.objects.create(
        swimmer=bob_swimmer,
        session=current_session,
        is_regular=False,
    )

    return {
        "current_year": current_year,
        "current_week": current_week,
        "alice_swimmer": alice_swimmer,
        "bob_swimmer": bob_swimmer,
        "past_session": past_session,
        "current_session": current_session,
        "future_session": future_session,
        "alice_registration": alice_registration,
        "bob_registration": bob_registration,
    }


def test_current_week_schedule(data):
    # Given
    year = 2026
    week = 30
    alice_swimmer = data["alice_swimmer"]
    bob_swimmer = data["bob_swimmer"]
    current_session = data["current_session"]
    alice_registration = data["alice_registration"]

    # When
    week_schedule_query = WeekScheduleQuery(
        year, week, alice_swimmer, only_user_sessions=False
    )
    week_schedule_query.load_schedule()
    schedule = week_schedule_query.schedule

    # Then
    assert week_schedule_query.user_registration_count == 1
    assert len(schedule) == 1
    assert current_session in schedule

    session = schedule[0]
    assert session.year == year
    assert session.week == week
    assert session.capacity == 10
    assert not session.is_cancelled

    assert len(session.user_registration) == 1

    assert session.user_registration[0].session == current_session
    assert session.user_registration[0].pk == alice_registration.pk
    assert not session.user_registration[0].is_cancelled
    assert session.user_registration[0].is_regular
    assert not session.user_registration[0].swimmer_is_coach

    assert len(session.swimmer_registrations) == 2

    assert session.swimmer_registrations[0].swimmer.pk == alice_swimmer.pk
    assert session.swimmer_registrations[0].session == current_session
    assert not session.swimmer_registrations[0].is_cancelled
    assert not session.swimmer_registrations[0].swimmer_is_coach
    assert session.swimmer_registrations[0].is_regular

    assert session.swimmer_registrations[1].swimmer.pk == bob_swimmer.pk
    assert session.swimmer_registrations[1].session == current_session
    assert not session.swimmer_registrations[1].is_cancelled
    assert not session.swimmer_registrations[1].is_regular
    assert not session.swimmer_registrations[1].swimmer_is_coach

    assert len(session.coach_registrations) == 0


def test_past_week_schedule(data):
    # Given
    year = 2026
    week = 29
    alice_swimmer = data["alice_swimmer"]
    past_session = data["past_session"]

    # When
    week_schedule_query = WeekScheduleQuery(
        year, week, alice_swimmer, only_user_sessions=False
    )
    week_schedule_query.load_schedule()
    schedule = week_schedule_query.schedule

    # Then
    assert week_schedule_query.user_registration_count == 0
    assert len(schedule) == 1
    assert past_session in schedule

    session = schedule[0]
    assert session.year == year
    assert session.week == week
    assert session.capacity == 8

    assert len(session.user_registration) == 0
    assert len(session.swimmer_registrations) == 0
    assert len(session.coach_registrations) == 0


def test_future_week_schedule(data):
    # Given
    year = 2026
    week = 31
    alice_swimmer = data["alice_swimmer"]
    current_session = data["current_session"]
    future_session = data["future_session"]
    alice_registration = data["alice_registration"]

    # When
    week_schedule_query = WeekScheduleQuery(
        year, week, alice_swimmer, only_user_sessions=False
    )
    week_schedule_query.load_schedule()
    schedule = week_schedule_query.schedule

    # Then
    assert week_schedule_query.user_registration_count == 1
    assert len(schedule) == 1
    assert future_session in schedule

    session = schedule[0]
    assert session.year == year
    assert session.week == week
    assert session.capacity == 12
    assert not session.is_cancelled

    assert len(session.user_registration) == 1

    # On ne modifie pas actuellement la séance de l'inscription on ne fait que l'importer
    assert session.user_registration[0].session == current_session
    assert session.user_registration[0].pk == alice_registration.pk
    assert not session.user_registration[0].is_cancelled
    assert session.user_registration[0].is_regular
    assert not session.user_registration[0].swimmer_is_coach

    assert len(session.swimmer_registrations) == 1
    assert len(session.coach_registrations) == 0


def test_not_regular_current_registration_should_not_be_imported_in_future(data):
    # Given
    year = 2026
    week = 31
    alice_swimmer = data["alice_swimmer"]
    future_session = data["future_session"]
    alice_registration = data["alice_registration"]
    alice_registration.is_regular = False
    alice_registration.save()

    # When
    week_schedule_query = WeekScheduleQuery(
        year, week, alice_swimmer, only_user_sessions=False
    )
    week_schedule_query.load_schedule()
    schedule = week_schedule_query.schedule

    # Then
    assert week_schedule_query.user_registration_count == 0
    assert len(schedule) == 1
    assert future_session in schedule

    session = schedule[0]
    assert session.year == year
    assert session.week == week
    assert session.capacity == 12

    assert len(session.user_registration) == 0
    assert len(session.swimmer_registrations) == 0
    assert len(session.coach_registrations) == 0


def test_cancelled_current_registration_should_be_imported_in_future(data):
    # Given
    year = 2026
    week = 31
    alice_swimmer = data["alice_swimmer"]
    current_session = data["current_session"]
    future_session = data["future_session"]
    alice_registration = data["alice_registration"]
    alice_registration.is_cancelled = True
    alice_registration.save()

    # When
    week_schedule_query = WeekScheduleQuery(
        year, week, alice_swimmer, only_user_sessions=False
    )
    week_schedule_query.load_schedule()
    schedule = week_schedule_query.schedule

    # Then
    assert week_schedule_query.user_registration_count == 1
    assert len(schedule) == 1
    assert future_session in schedule

    session = schedule[0]
    assert session.year == year
    assert session.week == week
    assert session.capacity == 12

    assert len(session.user_registration) == 1

    # On ne modifie pas actuellement la séance de l'inscription on ne fait que l'importer
    assert session.user_registration[0].session == current_session
    assert session.user_registration[0].pk == alice_registration.pk
    assert not session.user_registration[0].is_cancelled
    assert session.user_registration[0].is_regular
    assert not session.user_registration[0].swimmer_is_coach

    assert len(session.swimmer_registrations) == 1
    assert len(session.coach_registrations) == 0


def test_cancel_future_registration(data):
    # Given
    year = 2026
    week = 31
    alice_swimmer = data["alice_swimmer"]
    future_session = data["future_session"]
    alice_future_registration = SessionRegistration.objects.create(
        swimmer=alice_swimmer,
        session=future_session,
        is_regular=True,
        is_cancelled=True,
    )

    # When
    week_schedule_query = WeekScheduleQuery(
        year, week, alice_swimmer, only_user_sessions=False
    )
    week_schedule_query.load_schedule()
    schedule = week_schedule_query.schedule

    # Then
    assert week_schedule_query.user_registration_count == 0
    assert len(schedule) == 1
    assert future_session in schedule

    session = schedule[0]
    assert session.year == year
    assert session.week == week
    assert session.capacity == 12

    assert len(session.user_registration) == 1

    assert session.user_registration[0].session == future_session
    assert session.user_registration[0].pk == alice_future_registration.pk
    assert session.user_registration[0].is_cancelled
    assert session.user_registration[0].is_regular
    assert not session.user_registration[0].swimmer_is_coach

    assert len(session.swimmer_registrations) == 0
    assert len(session.coach_registrations) == 0


def test_future_session_does_not_exist(data):
    # Given
    year = 2026
    week = 31
    alice_swimmer = data["alice_swimmer"]
    current_session = data["current_session"]
    future_session = data["future_session"]
    alice_registration = data["alice_registration"]
    future_session.delete()

    # When
    week_schedule_query = WeekScheduleQuery(
        year, week, alice_swimmer, only_user_sessions=False
    )
    week_schedule_query.load_schedule()
    schedule = week_schedule_query.schedule

    # Then
    assert week_schedule_query.user_registration_count == 1
    assert len(schedule) == 1
    assert current_session in schedule

    session = schedule[0]
    assert session.year == year
    assert session.week == week
    assert session.capacity == 10

    assert len(session.user_registration) == 1

    # On ne modifie pas actuellement la séance de l'inscription on ne fait que l'importer
    assert session.user_registration[0].session == current_session
    assert session.user_registration[0].pk == alice_registration.pk
    assert not session.user_registration[0].is_cancelled
    assert session.user_registration[0].is_regular
    assert not session.user_registration[0].swimmer_is_coach

    assert len(session.swimmer_registrations) == 1
    assert len(session.coach_registrations) == 0


def test_current_week_schedule_not_only_user_sessions(data):
    # Given
    year = 2026
    week = 30
    alice_swimmer = data["alice_swimmer"]
    bob_swimmer = data["bob_swimmer"]
    tuesday_session = data["current_session"]
    alice_registration = data["alice_registration"]
    monday_session = WeeklySession.objects.create(
        year=year,
        week=week,
        weekday=1,
        start_hour=datetime.time(20, 0),
        stop_hour=datetime.time(21, 0),
        capacity=5,
    )

    # When
    week_schedule_query = WeekScheduleQuery(
        year, week, alice_swimmer, only_user_sessions=False
    )
    week_schedule_query.load_schedule()
    schedule = week_schedule_query.schedule

    # Then
    assert week_schedule_query.user_registration_count == 1
    assert len(schedule) == 2
    assert monday_session in schedule
    assert tuesday_session in schedule

    session = schedule[0]
    assert session.year == year
    assert session.week == week
    assert session.weekday == 1
    assert session.capacity == 5

    assert len(session.user_registration) == 0
    assert len(session.swimmer_registrations) == 0
    assert len(session.coach_registrations) == 0

    session = schedule[1]
    assert session.year == year
    assert session.week == week
    assert session.weekday == 2
    assert session.capacity == 10

    assert len(session.user_registration) == 1

    assert session.user_registration[0].session == tuesday_session
    assert session.user_registration[0].pk == alice_registration.pk
    assert not session.user_registration[0].is_cancelled
    assert session.user_registration[0].is_regular
    assert not session.user_registration[0].swimmer_is_coach

    assert len(session.swimmer_registrations) == 2

    assert session.swimmer_registrations[0].swimmer.pk == alice_swimmer.pk
    assert session.swimmer_registrations[0].session == tuesday_session
    assert not session.swimmer_registrations[0].is_cancelled
    assert not session.swimmer_registrations[0].swimmer_is_coach
    assert session.swimmer_registrations[0].is_regular

    assert session.swimmer_registrations[1].swimmer.pk == bob_swimmer.pk
    assert session.swimmer_registrations[1].session == tuesday_session
    assert not session.swimmer_registrations[1].is_cancelled
    assert not session.swimmer_registrations[1].is_regular
    assert not session.swimmer_registrations[1].swimmer_is_coach

    assert len(session.coach_registrations) == 0


def test_current_week_schedule_only_user_sessions(data):
    # Given
    year = 2026
    week = 30
    alice_swimmer = data["alice_swimmer"]
    bob_swimmer = data["bob_swimmer"]
    tuesday_session = data["current_session"]
    alice_registration = data["alice_registration"]
    monday_session = WeeklySession.objects.create(
        year=year,
        week=week,
        weekday=1,
        start_hour=datetime.time(20, 0),
        stop_hour=datetime.time(21, 0),
        capacity=5,
    )

    # When
    week_schedule_query = WeekScheduleQuery(
        year, week, alice_swimmer, only_user_sessions=True
    )
    week_schedule_query.load_schedule()
    schedule = week_schedule_query.schedule

    # Then
    assert week_schedule_query.user_registration_count == 1
    assert len(schedule) == 1
    assert monday_session not in schedule
    assert tuesday_session in schedule

    session = schedule[0]
    assert session.year == year
    assert session.week == week
    assert session.weekday == 2
    assert session.capacity == 10

    assert len(session.user_registration) == 1

    assert session.user_registration[0].session == tuesday_session
    assert session.user_registration[0].pk == alice_registration.pk
    assert not session.user_registration[0].is_cancelled
    assert session.user_registration[0].is_regular
    assert not session.user_registration[0].swimmer_is_coach

    assert len(session.swimmer_registrations) == 2

    assert session.swimmer_registrations[0].swimmer.pk == alice_swimmer.pk
    assert session.swimmer_registrations[0].session == tuesday_session
    assert not session.swimmer_registrations[0].is_cancelled
    assert not session.swimmer_registrations[0].swimmer_is_coach
    assert session.swimmer_registrations[0].is_regular

    assert session.swimmer_registrations[1].swimmer.pk == bob_swimmer.pk
    assert session.swimmer_registrations[1].session == tuesday_session
    assert not session.swimmer_registrations[1].is_cancelled
    assert not session.swimmer_registrations[1].is_regular
    assert not session.swimmer_registrations[1].swimmer_is_coach

    assert len(session.coach_registrations) == 0


def test_current_week_schedule_bob_is_coach(data):
    # Given
    year = 2026
    week = 30
    alice_swimmer = data["alice_swimmer"]
    bob_swimmer = data["bob_swimmer"]
    current_session = data["current_session"]
    alice_registration = data["alice_registration"]
    bob_registration = data["bob_registration"]
    bob_registration.swimmer_is_coach = True
    bob_registration.save()

    # When
    week_schedule_query = WeekScheduleQuery(
        year, week, alice_swimmer, only_user_sessions=False
    )
    week_schedule_query.load_schedule()
    schedule = week_schedule_query.schedule

    # Then
    assert week_schedule_query.user_registration_count == 1
    assert len(schedule) == 1
    assert current_session in schedule

    session = schedule[0]
    assert session.year == year
    assert session.week == week
    assert session.capacity == 10

    assert len(session.user_registration) == 1

    assert session.user_registration[0].session == current_session
    assert session.user_registration[0].pk == alice_registration.pk
    assert not session.user_registration[0].is_cancelled
    assert session.user_registration[0].is_regular
    assert not session.user_registration[0].swimmer_is_coach

    assert len(session.swimmer_registrations) == 1

    assert session.swimmer_registrations[0].swimmer.pk == alice_swimmer.pk
    assert session.swimmer_registrations[0].session == current_session
    assert not session.swimmer_registrations[0].is_cancelled
    assert not session.swimmer_registrations[0].swimmer_is_coach
    assert session.swimmer_registrations[0].is_regular

    assert len(session.coach_registrations) == 1

    assert session.coach_registrations[0].swimmer.pk == bob_swimmer.pk
    assert session.coach_registrations[0].session == current_session
    assert not session.coach_registrations[0].is_cancelled
    assert not session.coach_registrations[0].is_regular
    assert session.coach_registrations[0].swimmer_is_coach


def test_current_week_schedule_alice_is_coach(data):
    # Given
    year = 2026
    week = 30
    alice_swimmer = data["alice_swimmer"]
    bob_swimmer = data["bob_swimmer"]
    current_session = data["current_session"]
    alice_registration = data["alice_registration"]
    alice_registration.swimmer_is_coach = True
    alice_registration.save()

    # When
    week_schedule_query = WeekScheduleQuery(
        year, week, alice_swimmer, only_user_sessions=False
    )
    week_schedule_query.load_schedule()
    schedule = week_schedule_query.schedule

    # Then
    assert week_schedule_query.user_registration_count == 0
    assert len(schedule) == 1
    assert current_session in schedule

    session = schedule[0]
    assert session.year == year
    assert session.week == week
    assert session.capacity == 10

    assert len(session.user_registration) == 1

    assert session.user_registration[0].session == current_session
    assert session.user_registration[0].pk == alice_registration.pk
    assert not session.user_registration[0].is_cancelled
    assert session.user_registration[0].is_regular
    assert session.user_registration[0].swimmer_is_coach

    assert len(session.swimmer_registrations) == 1

    assert session.swimmer_registrations[0].swimmer.pk == bob_swimmer.pk
    assert session.swimmer_registrations[0].session == current_session
    assert not session.swimmer_registrations[0].is_cancelled
    assert not session.swimmer_registrations[0].is_regular
    assert not session.swimmer_registrations[0].swimmer_is_coach

    assert len(session.coach_registrations) == 1

    assert session.coach_registrations[0].swimmer.pk == alice_swimmer.pk
    assert session.coach_registrations[0].session == current_session
    assert not session.coach_registrations[0].is_cancelled
    assert session.coach_registrations[0].is_regular
    assert session.coach_registrations[0].swimmer_is_coach


def test_future_week_schedule_bob_is_coach(data):
    # Given
    year = 2026
    week = 31
    alice_swimmer = data["alice_swimmer"]
    current_session = data["current_session"]
    future_session = data["future_session"]
    alice_registration = data["alice_registration"]
    bob_registration = data["bob_registration"]
    bob_registration.swimmer_is_coach = True
    bob_registration.save()

    # When
    week_schedule_query = WeekScheduleQuery(
        year, week, alice_swimmer, only_user_sessions=False
    )
    week_schedule_query.load_schedule()
    schedule = week_schedule_query.schedule

    # Then
    assert week_schedule_query.user_registration_count == 1
    assert len(schedule) == 1
    assert future_session in schedule

    session = schedule[0]
    assert session.year == year
    assert session.week == week
    assert session.capacity == 12

    assert len(session.user_registration) == 1

    # On ne modifie pas actuellement la séance de l'inscription on ne fait que l'importer
    assert session.user_registration[0].session == current_session
    assert session.user_registration[0].pk == alice_registration.pk
    assert not session.user_registration[0].is_cancelled
    assert session.user_registration[0].is_regular
    assert not session.user_registration[0].swimmer_is_coach

    assert len(session.swimmer_registrations) == 1

    assert session.swimmer_registrations[0].swimmer.pk == alice_swimmer.pk
    # On ne modifie pas actuellement la séance de l'inscription on ne fait que l'importer
    assert session.swimmer_registrations[0].session == current_session
    assert not session.swimmer_registrations[0].is_cancelled
    assert not session.swimmer_registrations[0].swimmer_is_coach
    assert session.swimmer_registrations[0].is_regular

    assert len(session.coach_registrations) == 0


def test_future_week_schedule_alice_is_coach(data):
    # Given
    year = 2026
    week = 31
    alice_swimmer = data["alice_swimmer"]
    current_session = data["current_session"]
    future_session = data["future_session"]
    alice_registration = data["alice_registration"]
    alice_registration.swimmer_is_coach = True
    alice_registration.save()

    # When
    week_schedule_query = WeekScheduleQuery(
        year, week, alice_swimmer, only_user_sessions=False
    )
    week_schedule_query.load_schedule()
    schedule = week_schedule_query.schedule

    # Then
    assert week_schedule_query.user_registration_count == 0
    assert len(schedule) == 1
    assert future_session in schedule

    session = schedule[0]
    assert session.year == year
    assert session.week == week
    assert session.capacity == 12

    assert len(session.user_registration) == 1

    # On ne modifie pas actuellement la séance de l'inscription on ne fait que l'importer
    assert session.user_registration[0].session == current_session
    assert session.user_registration[0].pk == alice_registration.pk
    assert not session.user_registration[0].is_cancelled
    assert session.user_registration[0].is_regular
    assert session.user_registration[0].swimmer_is_coach

    assert len(session.swimmer_registrations) == 0

    assert len(session.coach_registrations) == 1

    assert session.coach_registrations[0].swimmer.pk == alice_swimmer.pk
    # On ne modifie pas actuellement la séance de l'inscription on ne fait que l'importer
    assert session.coach_registrations[0].session == current_session
    assert not session.coach_registrations[0].is_cancelled
    assert session.coach_registrations[0].swimmer_is_coach
    assert session.coach_registrations[0].is_regular


def test_current_week_schedule_session_is_cancelled(data):
    # Given
    year = 2026
    week = 30
    alice_swimmer = data["alice_swimmer"]
    bob_swimmer = data["bob_swimmer"]
    current_session = data["current_session"]
    alice_registration = data["alice_registration"]
    current_session.is_cancelled = True
    current_session.save()

    # When
    week_schedule_query = WeekScheduleQuery(
        year, week, alice_swimmer, only_user_sessions=False
    )
    week_schedule_query.load_schedule()
    schedule = week_schedule_query.schedule

    # Then
    assert week_schedule_query.user_registration_count == 0
    assert len(schedule) == 1
    assert current_session in schedule

    session = schedule[0]
    assert session.year == year
    assert session.week == week
    assert session.capacity == 10
    assert session.is_cancelled

    assert len(session.user_registration) == 1

    assert session.user_registration[0].session == current_session
    assert session.user_registration[0].pk == alice_registration.pk
    assert not session.user_registration[0].is_cancelled
    assert session.user_registration[0].is_regular
    assert not session.user_registration[0].swimmer_is_coach

    assert len(session.swimmer_registrations) == 2

    assert session.swimmer_registrations[0].swimmer.pk == alice_swimmer.pk
    assert session.swimmer_registrations[0].session == current_session
    assert not session.swimmer_registrations[0].is_cancelled
    assert not session.swimmer_registrations[0].swimmer_is_coach
    assert session.swimmer_registrations[0].is_regular

    assert session.swimmer_registrations[1].swimmer.pk == bob_swimmer.pk
    assert session.swimmer_registrations[1].session == current_session
    assert not session.swimmer_registrations[1].is_cancelled
    assert not session.swimmer_registrations[1].is_regular
    assert not session.swimmer_registrations[1].swimmer_is_coach

    assert len(session.coach_registrations) == 0


def test_current_week_schedule_session_is_cancelled_only_user_sessions(data):
    # Given
    year = 2026
    week = 30
    alice_swimmer = data["alice_swimmer"]
    bob_swimmer = data["bob_swimmer"]
    current_session = data["current_session"]
    alice_registration = data["alice_registration"]
    current_session.is_cancelled = True
    current_session.save()

    # When
    week_schedule_query = WeekScheduleQuery(
        year, week, alice_swimmer, only_user_sessions=True
    )
    week_schedule_query.load_schedule()
    schedule = week_schedule_query.schedule

    # Then
    assert week_schedule_query.user_registration_count == 0
    assert len(schedule) == 1
    assert current_session in schedule

    session = schedule[0]
    assert session.year == year
    assert session.week == week
    assert session.capacity == 10
    assert session.is_cancelled

    assert len(session.user_registration) == 1

    assert session.user_registration[0].session == current_session
    assert session.user_registration[0].pk == alice_registration.pk
    assert not session.user_registration[0].is_cancelled
    assert session.user_registration[0].is_regular
    assert not session.user_registration[0].swimmer_is_coach

    assert len(session.swimmer_registrations) == 2

    assert session.swimmer_registrations[0].swimmer.pk == alice_swimmer.pk
    assert session.swimmer_registrations[0].session == current_session
    assert not session.swimmer_registrations[0].is_cancelled
    assert not session.swimmer_registrations[0].swimmer_is_coach
    assert session.swimmer_registrations[0].is_regular

    assert session.swimmer_registrations[1].swimmer.pk == bob_swimmer.pk
    assert session.swimmer_registrations[1].session == current_session
    assert not session.swimmer_registrations[1].is_cancelled
    assert not session.swimmer_registrations[1].is_regular
    assert not session.swimmer_registrations[1].swimmer_is_coach

    assert len(session.coach_registrations) == 0


def test_future_week_schedule_session_is_cancelled(data):
    # Given
    year = 2026
    week = 31
    alice_swimmer = data["alice_swimmer"]
    current_session = data["current_session"]
    future_session = data["future_session"]
    alice_registration = data["alice_registration"]
    future_session.is_cancelled = True
    future_session.save()

    # When
    week_schedule_query = WeekScheduleQuery(
        year, week, alice_swimmer, only_user_sessions=False
    )
    week_schedule_query.load_schedule()
    schedule = week_schedule_query.schedule

    # Then
    assert week_schedule_query.user_registration_count == 0
    assert len(schedule) == 1
    assert future_session in schedule

    session = schedule[0]
    assert session.year == year
    assert session.week == week
    assert session.capacity == 12
    assert session.is_cancelled

    assert len(session.user_registration) == 1

    # On ne modifie pas actuellement la séance de l'inscription on ne fait que l'importer
    assert session.user_registration[0].session == current_session
    assert session.user_registration[0].pk == alice_registration.pk
    assert not session.user_registration[0].is_cancelled
    assert session.user_registration[0].is_regular
    assert not session.user_registration[0].swimmer_is_coach

    assert len(session.swimmer_registrations) == 1
    assert len(session.coach_registrations) == 0


def test_future_week_schedule_session_is_cancelled_only_user_sessions(data):
    # Given
    year = 2026
    week = 31
    alice_swimmer = data["alice_swimmer"]
    current_session = data["current_session"]
    future_session = data["future_session"]
    alice_registration = data["alice_registration"]
    future_session.is_cancelled = True
    future_session.save()

    # When
    week_schedule_query = WeekScheduleQuery(
        year, week, alice_swimmer, only_user_sessions=True
    )
    week_schedule_query.load_schedule()
    schedule = week_schedule_query.schedule

    # Then
    assert week_schedule_query.user_registration_count == 0
    assert len(schedule) == 1
    assert future_session in schedule

    session = schedule[0]
    assert session.year == year
    assert session.week == week
    assert session.capacity == 12
    assert session.is_cancelled

    assert len(session.user_registration) == 1

    # On ne modifie pas actuellement la séance de l'inscription on ne fait que l'importer
    assert session.user_registration[0].session == current_session
    assert session.user_registration[0].pk == alice_registration.pk
    assert not session.user_registration[0].is_cancelled
    assert session.user_registration[0].is_regular
    assert not session.user_registration[0].swimmer_is_coach

    assert len(session.swimmer_registrations) == 1
    assert len(session.coach_registrations) == 0
