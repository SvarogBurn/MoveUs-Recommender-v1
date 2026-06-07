"""Seed demo users and events from ml/data/ CSVs for local algorithm demonstrations.

Usage:
    python manage.py seed_demo_data                          # 20 users, 100 events, 10 history, follows
    python manage.py seed_demo_data --users 50 --events 200
    python manage.py seed_demo_data --clear                  # wipe then re-seed
    python manage.py seed_demo_data --clear --users 0 --events 0  # wipe only

Demo credentials: demo_<id>@moveus.demo / demo123
"""

import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction

from main.activity.models import Activity
from main.event.models import Event, EventMember
from main.location.models import Location
from main.social.models import Follow
from main.user.models import (
    User,
    UserAvailability,
    UserParticipationGroup,
    UserPreferredActivity,
    UserPreferences,
)
from shared.enums import ActivityKind, EventPhase, EventRating, MemberRole

DEMO_USERNAME_PREFIX = "demo_"
DEMO_TITLE_PREFIX = "[Demo] "

# Shift synthetic 2023-era events into the future so the UI shows them as upcoming.
# 2023-01-01 + 1278 days ≈ 2026-07-04.
_TIME_OFFSET = timedelta(days=1278)


def _parse_list(raw: str) -> list[int]:
    """Parse a CSV field that may be a single int or a comma-separated list."""
    return [int(x) for x in raw.split(",") if x.strip()]


def _activity_label(activity_id: int) -> str:
    try:
        return ActivityKind(activity_id).name.replace("_", " ").title()
    except ValueError:
        return f"Activity {activity_id}"


class Command(BaseCommand):
    help = "Seed demo users and events from ml/data/ CSVs for local demonstrations."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=20,
                            help="Number of users to seed (default 20)")
        parser.add_argument("--events", type=int, default=100,
                            help="Number of events to seed (default 100)")
        parser.add_argument("--history", type=int, default=10,
                            help="Past attendances per user for ML history features (default 10)")
        parser.add_argument("--no-follows", action="store_true",
                            help="Skip seeding follow relationships between demo users")
        parser.add_argument("--clear", action="store_true",
                            help="Delete existing demo data before seeding")

    def handle(self, *args, **options):
        if options["clear"]:
            self._clear()

        n_users = options["users"]
        n_events = options["events"]

        if n_users == 0 and n_events == 0:
            return

        data_dir = Path(settings.BASE_DIR) / "ml" / "data"

        with transaction.atomic():
            self._ensure_activities()
            created_users = self._seed_users(data_dir, n_users)
            created_events = self._seed_events(data_dir, n_events)
            created_history = self._seed_history(options["history"])
            created_follows = 0 if options["no_follows"] else self._seed_follows()

        self.stdout.write(self.style.SUCCESS(
            f"Done.\n"
            f"  {created_users} users, {created_events} scheduled events\n"
            f"  {created_history} past attendances (history features)\n"
            f"  {created_follows} follow relationships\n"
            f"Login: demo_<id>@moveus.demo / demo123  (e.g. demo_0@moveus.demo)"
        ))

    # ------------------------------------------------------------------
    def _clear(self):
        demo_events = Event.objects.filter(title__startswith=DEMO_TITLE_PREFIX)
        location_ids = list(demo_events.values_list("location_id", flat=True))
        n_ev, _ = demo_events.delete()
        Location.objects.filter(id__in=location_ids).delete()

        n_usr, _ = User.objects.filter(
            username__startswith=DEMO_USERNAME_PREFIX
        ).delete()

        self.stdout.write(f"Cleared {n_usr} demo users and {n_ev} demo events.")

    # ------------------------------------------------------------------
    def _ensure_activities(self):
        existing_ids = set(Activity.objects.values_list("id", flat=True))
        new_activities = [
            Activity(id=kind.value)
            for kind in ActivityKind
            if kind.value not in existing_ids
        ]
        if new_activities:
            Activity.objects.bulk_create(new_activities)

    # ------------------------------------------------------------------
    def _seed_users(self, data_dir: Path, n: int) -> int:
        if n == 0:
            return 0

        csv_path = data_dir / "users.csv"
        if not csv_path.exists():
            self.stderr.write(
                self.style.ERROR(f"Missing {csv_path}. Run: python -m ml.gen.timeline")
            )
            return 0

        hashed_pw = make_password("demo123")
        valid_activity_ids = set(Activity.objects.values_list("id", flat=True))
        created = 0

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= n:
                    break

                uid = int(row["user_id"])
                username = f"{DEMO_USERNAME_PREFIX}{uid}"
                email = f"demo_{uid}@moveus.demo"

                if User.objects.filter(username=username).exists():
                    continue

                user = User.objects.create(
                    username=username,
                    email=email,
                    password=hashed_pw,
                    first_name="Demo",
                    last_name=f"User {uid}",
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    gender=int(float(row["gender"])),
                    is_active=True,
                )

                prefs = UserPreferences.objects.create(
                    user=user,
                    preferred_session_duration=int(float(row["preferred_session_duration"])),
                    organizing_openness=int(float(row["organizing_openness"])),
                    leadership_inclination=int(float(row["leadership_inclination"])),
                    max_travel_distance=int(float(row["max_travel_distance"])),
                    weekly_activity_target=int(float(row["weekly_activity_target"])),
                    pushes_through_discomfort=int(float(row["pushes_through_discomfort"])),
                    preferred_group_size=int(float(row["preferred_group_size"])),
                    acquaintance_preference=int(float(row["acquaintance_preference"])),
                    enjoys_meeting_new_people=int(float(row["enjoys_meeting_new_people"])),
                    activity_vs_social=int(float(row["activity_vs_social"])),
                    motivated_by_competition=int(float(row["motivated_by_competition"])),
                    planning_horizon=int(float(row["planning_horizon"])),
                    feels_like_burden=int(float(row["feels_like_burden"])),
                )

                pref_acts = _parse_list(row["preferred_activities"])
                pref_skills = _parse_list(row["preferred_skills"])
                for act_id, skill in zip(pref_acts, pref_skills):
                    if act_id in valid_activity_ids:
                        UserPreferredActivity.objects.create(
                            preferences=prefs,
                            activity_id=act_id,
                            skill_level=skill,
                        )

                avail_days = _parse_list(row["availability_days"])
                avail_times = _parse_list(row["availability_times"])
                UserAvailability.objects.bulk_create(
                    [
                        UserAvailability(preferences=prefs, day_of_week=d, time_of_day=t)
                        for d in avail_days
                        for t in avail_times
                    ],
                    ignore_conflicts=True,
                )

                p_groups = _parse_list(row["participation_groups"])
                UserParticipationGroup.objects.bulk_create(
                    [UserParticipationGroup(preferences=prefs, group_kind=g) for g in p_groups],
                    ignore_conflicts=True,
                )

                created += 1

        return created

    # ------------------------------------------------------------------
    def _seed_events(self, data_dir: Path, n: int) -> int:
        if n == 0:
            return 0

        csv_path = data_dir / "events.csv"
        if not csv_path.exists():
            self.stderr.write(
                self.style.ERROR(f"Missing {csv_path}. Run: python -m ml.gen.timeline")
            )
            return 0

        valid_activity_ids = set(Activity.objects.values_list("id", flat=True))
        created = 0

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= n:
                    break

                act_id = int(row["activity_id"])
                if act_id not in valid_activity_ids:
                    continue

                try:
                    start_dt = (
                        datetime.fromisoformat(row["start_time"]).replace(tzinfo=timezone.utc)
                        + _TIME_OFFSET
                    )
                    end_dt = (
                        datetime.fromisoformat(row["end_time"]).replace(tzinfo=timezone.utc)
                        + _TIME_OFFSET
                    )
                except ValueError:
                    continue

                raw_max = row.get("max_participants", "").strip()
                max_participants = int(float(raw_max)) if raw_max else 10

                location = Location.objects.create(
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    name=f"{_activity_label(act_id)} venue",
                    city="Zagreb",
                )

                Event.objects.create(
                    title=f"{DEMO_TITLE_PREFIX}{_activity_label(act_id)} Session",
                    start_time=start_dt,
                    end_time=end_dt,
                    location=location,
                    activity_id=act_id,
                    skill_level=int(float(row["skill_level"])),
                    max_participants=max_participants,
                    phase=EventPhase.SCHEDULED,
                )
                created += 1

        return created

    # ------------------------------------------------------------------
    def _seed_history(self, n_per_user: int) -> int:
        """Create finished past events + attendance records so history features are non-zero.

        Each demo user gets n_per_user attendances distributed across their preferred
        activities. This populates act_aff, act_seen, clu_aff, clu_seen, total_joins,
        avg_rating — the features that drive strong personalisation.
        """
        if n_per_user == 0:
            return 0

        demo_users = list(
            User.objects.filter(username__startswith=DEMO_USERNAME_PREFIX)
            .prefetch_related("preferences__preferred_activities")
        )
        if not demo_users:
            return 0

        now = datetime.now(timezone.utc)
        created = 0

        for user in demo_users:
            try:
                pref_acts = list(
                    user.preferences.preferred_activities.values_list("activity_id", flat=True)
                )
            except Exception:
                pref_acts = []

            if not pref_acts:
                continue

            for i in range(n_per_user):
                act_id = pref_acts[i % len(pref_acts)]
                # Spread attendances over the last 6 months, most recent first
                start_dt = now - timedelta(days=(i + 1) * 10)
                end_dt = start_dt + timedelta(hours=1, minutes=30)

                location = Location.objects.create(
                    latitude=user.latitude + random.uniform(-0.01, 0.01),
                    longitude=user.longitude + random.uniform(-0.01, 0.01),
                    city="Zagreb",
                )
                event = Event.objects.create(
                    title=f"{DEMO_TITLE_PREFIX}{_activity_label(act_id)} Session",
                    start_time=start_dt,
                    end_time=end_dt,
                    location=location,
                    activity_id=act_id,
                    skill_level=1,
                    max_participants=10,
                    phase=EventPhase.FINISHED,
                )
                EventMember.objects.create(
                    user=user,
                    event=event,
                    role=MemberRole.PARTICIPANT,
                    has_participated=True,
                    participates=False,
                    score=EventRating.GREAT,
                )
                created += 1

        return created

    # ------------------------------------------------------------------
    def _seed_follows(self) -> int:
        """Have demo users follow each other in a ring + a few random cross-links.

        Follows don't affect the ML ranking directly but make the social graph
        non-empty so the app UI (profiles, activity feeds) looks populated.
        """
        demo_users = list(
            User.objects.filter(username__startswith=DEMO_USERNAME_PREFIX).order_by("id")
        )
        if len(demo_users) < 2:
            return 0

        existing = set(
            Follow.objects.filter(
                follower__in=demo_users, following__in=demo_users
            ).values_list("follower_id", "following_id")
        )

        to_create = []
        n = len(demo_users)

        # Ring: each user follows the next 3 (wraps around)
        for i, user in enumerate(demo_users):
            for step in range(1, min(4, n)):
                target = demo_users[(i + step) % n]
                if (user.pk, target.pk) not in existing:
                    to_create.append(Follow(follower=user, following=target))

        Follow.objects.bulk_create(to_create, ignore_conflicts=True)
        return len(to_create)
