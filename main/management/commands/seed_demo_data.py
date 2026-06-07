"""Seed demo users and events from ml/data/ CSVs for local algorithm demonstrations.

Usage:
    python manage.py seed_demo_data                          # 20 users, 25 events
    python manage.py seed_demo_data --users 20 --events 25
    python manage.py seed_demo_data --clear                  # wipe then re-seed
    python manage.py seed_demo_data --clear --users 0 --events 0  # wipe only

Demo credentials: demo_<id>@moveus.demo / demo123

Events are identified for cleanup by a hidden marker at the end of their description
(\\n#demo), so titles can be fully realistic faker-generated strings.
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

try:
    from faker import Faker
    _fake = Faker("en_US")
    _fake.seed_instance(42)
    _FAKER_AVAILABLE = True
except ImportError:
    _FAKER_AVAILABLE = False

DEMO_USERNAME_PREFIX = "demo_"
# Hidden marker appended to every demo event description — used for cleanup.
_DEMO_MARKER = "\n#demo"

# Shift synthetic 2023-era events into the future so the UI shows them as upcoming.
_TIME_OFFSET = timedelta(days=1278)  # 2023-01-01 + 1278 d ≈ 2026-07-04

_ZAGREB_VENUES = [
    "Maksimir Park", "Bundek Lake", "Jarun Lake", "Sava Embankment",
    "Medvednica Mountain", "Salata Sports Centre", "Dom Sportova",
    "Šalata Recreation Area", "Bundek Sports Complex", "City Park Zagreb",
]

_SKILL_LABELS = {0: "Beginner", 1: "Open Level", 2: "Intermediate", 3: "Advanced"}
_SKILL_DESC   = {
    0: "complete beginners and newcomers",
    1: "all levels — everyone welcome",
    2: "intermediate players looking to improve",
    3: "advanced athletes who want a serious workout",
}


def _parse_list(raw: str) -> list[int]:
    return [int(x) for x in raw.split(",") if x.strip()]


def _activity_label(activity_id: int) -> str:
    try:
        return ActivityKind(activity_id).name.replace("_", " ").title()
    except ValueError:
        return f"Activity {activity_id}"


def _event_title(activity_label: str, skill_level: int) -> str:
    skill = _SKILL_LABELS.get(skill_level, "Open Level")
    venue = random.choice(_ZAGREB_VENUES)
    time_word = random.choice(["Morning", "Afternoon", "Evening", "Weekend", "Saturday", "Sunday"])
    templates = [
        f"{time_word} {activity_label} at {venue}",
        f"{activity_label} Session — {skill}",
        f"Weekly {activity_label} Meetup",
        f"{activity_label} at {venue}",
        f"Open {activity_label} — {skill}",
        f"{skill} {activity_label} Training",
        f"{activity_label} Group — {venue}",
    ]
    if _FAKER_AVAILABLE:
        templates += [
            f"{_fake.first_name()}'s {activity_label} Group",
            f"{activity_label} near {_fake.street_name()}",
        ]
    return random.choice(templates)


def _event_description(activity_label: str, skill_level: int, max_participants: int) -> str:
    skill_desc = _SKILL_DESC.get(skill_level, "all levels")
    intros = [
        f"We're looking for people to join our {activity_label.lower()} session in Zagreb.",
        f"Come join us for a great {activity_label.lower()} meetup!",
        f"Organising a {activity_label.lower()} session — everyone is welcome.",
        f"Join our {activity_label.lower()} group for a fun and active session.",
        f"A {activity_label.lower()} session open to {skill_desc}.",
    ]
    middles = [
        f"Suitable for {skill_desc}.",
        f"We welcome {skill_desc}.",
        f"Open to {skill_desc} — no judgement, just sport.",
    ]
    outros = [
        f"Limited to {max_participants} participants, so sign up early!",
        f"Max {max_participants} spots — first come, first served.",
        f"Bring water and appropriate gear. {max_participants} spots available.",
        f"Equipment can be shared. Maximum {max_participants} people.",
    ]
    extra = ""
    if _FAKER_AVAILABLE:
        extra = f" {_fake.sentence()}"
    desc = f"{random.choice(intros)} {random.choice(middles)}{extra} {random.choice(outros)}"
    return desc + _DEMO_MARKER


class Command(BaseCommand):
    help = "Seed demo users and events from ml/data/ CSVs for local demonstrations."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=20,
                            help="Number of users to seed (default 20)")
        parser.add_argument("--events", type=int, default=25,
                            help="Number of scheduled events to seed (default 25)")
        parser.add_argument("--history", type=int, default=12,
                            help="Past attendances per user for ML history features (default 12)")
        parser.add_argument("--no-follows", action="store_true",
                            help="Skip seeding follow relationships")
        parser.add_argument("--clear", action="store_true",
                            help="Delete existing demo data before seeding")

    def handle(self, *args, **options):
        if not _FAKER_AVAILABLE:
            self.stdout.write(self.style.WARNING(
                "faker not installed — using template-based titles/descriptions."
            ))

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
            created_members = self._seed_event_members()
            created_history = self._seed_history(options["history"])
            created_follows = 0 if options["no_follows"] else self._seed_follows()

        self.stdout.write(self.style.SUCCESS(
            f"Done.\n"
            f"  {created_users} users,  {created_events} scheduled events\n"
            f"  {created_members} event sign-ups (events now partially filled)\n"
            f"  {created_history} past attendances (history features populated)\n"
            f"  {created_follows} follow relationships\n"
            f"Login: demo_<id>@moveus.demo / demo123  (e.g. demo_0@moveus.demo)"
        ))

    # ------------------------------------------------------------------
    def _clear(self):
        from django.db import connection

        # --- demo events ---
        demo_events = Event.objects.filter(description__endswith=_DEMO_MARKER)
        location_ids = list(demo_events.values_list("location_id", flat=True))
        n_ev, _ = demo_events.delete()
        Location.objects.filter(id__in=location_ids).delete()

        # --- demo users ---
        # We delete related objects explicitly rather than letting Django's ORM
        # cascade collector run, because main_app_directchat (a legacy table) does
        # not exist on a fresh demo DB and causes the collector to fail.
        demo_user_ids = list(
            User.objects.filter(username__startswith=DEMO_USERNAME_PREFIX)
            .values_list("id", flat=True)
        )
        n_usr = len(demo_user_ids)
        if demo_user_ids:
            # 1. social graph
            Follow.objects.filter(follower_id__in=demo_user_ids).delete()
            Follow.objects.filter(following_id__in=demo_user_ids).delete()
            # 2. event memberships (EventMember cascade from Event already deleted above,
            #    but users may have memberships on non-demo events too)
            EventMember.objects.filter(user_id__in=demo_user_ids).delete()
            # 3. preferences (UserAvailability / UserPreferredActivity / UserParticipationGroup
            #    cascade from UserPreferences via DB FK)
            UserPreferences.objects.filter(user_id__in=demo_user_ids).delete()
            # 4. user rows — no remaining FKs pointing at them from migrated tables
            with connection.cursor() as cursor:
                placeholders = ",".join(["%s"] * len(demo_user_ids))
                cursor.execute(
                    f'DELETE FROM "{User._meta.db_table}" WHERE "id" IN ({placeholders})',
                    demo_user_ids,
                )

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
            self.stderr.write(self.style.ERROR(
                f"Missing {csv_path}. Run: python -m ml.gen.timeline"
            ))
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
                            preferences=prefs, activity_id=act_id, skill_level=skill,
                        )

                avail_days = _parse_list(row["availability_days"])
                avail_times = _parse_list(row["availability_times"])
                UserAvailability.objects.bulk_create(
                    [
                        UserAvailability(preferences=prefs, day_of_week=d, time_of_day=t)
                        for d in avail_days for t in avail_times
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
            self.stderr.write(self.style.ERROR(
                f"Missing {csv_path}. Run: python -m ml.gen.timeline"
            ))
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
                act_label = _activity_label(act_id)
                skill_level = int(float(row["skill_level"]))

                location = Location.objects.create(
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    name=random.choice(_ZAGREB_VENUES),
                    city="Zagreb",
                )
                Event.objects.create(
                    title=_event_title(act_label, skill_level),
                    description=_event_description(act_label, skill_level, max_participants),
                    start_time=start_dt,
                    end_time=end_dt,
                    location=location,
                    activity_id=act_id,
                    skill_level=skill_level,
                    max_participants=max_participants,
                    phase=EventPhase.SCHEDULED,
                )
                created += 1

        return created

    # ------------------------------------------------------------------
    def _seed_event_members(self) -> int:
        """Sign demo users up for scheduled events so events look populated (40–80% fill)."""
        demo_users = list(User.objects.filter(username__startswith=DEMO_USERNAME_PREFIX))
        demo_events = list(
            Event.objects.filter(
                description__endswith=_DEMO_MARKER, phase=EventPhase.SCHEDULED
            )
        )
        if not demo_users or not demo_events:
            return 0

        existing = set(
            EventMember.objects.filter(event__in=demo_events, user__in=demo_users)
            .values_list("event_id", "user_id")
        )
        to_create = []
        for event in demo_events:
            max_p = event.max_participants or 10
            low  = max(2, int(max_p * 0.40))
            high = min(len(demo_users), max(low + 1, int(max_p * 0.80)))
            n_members = random.randint(low, high)
            participants = random.sample(demo_users, min(n_members, len(demo_users)))

            for j, user in enumerate(participants):
                if (event.pk, user.pk) in existing:
                    continue
                role = MemberRole.ORGANIZER if j == 0 else MemberRole.PARTICIPANT
                to_create.append(EventMember(
                    user=user,
                    event=event,
                    role=role,
                    has_participated=True,
                    participates=True,
                ))

        EventMember.objects.bulk_create(to_create, ignore_conflicts=True)
        return len(to_create)

    # ------------------------------------------------------------------
    def _seed_history(self, n_per_user: int) -> int:
        """Create finished past events + attendance records so history features are non-zero."""
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
                act_label = _activity_label(act_id)
                start_dt = now - timedelta(days=(i + 1) * 10)
                end_dt = start_dt + timedelta(hours=1, minutes=30)

                location = Location.objects.create(
                    latitude=user.latitude + random.uniform(-0.01, 0.01),
                    longitude=user.longitude + random.uniform(-0.01, 0.01),
                    name=random.choice(_ZAGREB_VENUES),
                    city="Zagreb",
                )
                event = Event.objects.create(
                    title=_event_title(act_label, 1),
                    description=_event_description(act_label, 1, 10),
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
        """Each demo user follows the next 7 others (ring), giving everyone ≥ 7 followers."""
        demo_users = list(
            User.objects.filter(username__startswith=DEMO_USERNAME_PREFIX).order_by("id")
        )
        n = len(demo_users)
        if n < 2:
            return 0

        steps = min(7, n - 1)
        existing = set(
            Follow.objects.filter(follower__in=demo_users, following__in=demo_users)
            .values_list("follower_id", "following_id")
        )
        to_create = [
            Follow(follower=demo_users[i], following=demo_users[(i + step) % n])
            for i in range(n)
            for step in range(1, steps + 1)
            if (demo_users[i].pk, demo_users[(i + step) % n].pk) not in existing
        ]
        Follow.objects.bulk_create(to_create, ignore_conflicts=True)
        return len(to_create)
