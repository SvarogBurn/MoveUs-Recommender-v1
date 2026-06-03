import datetime

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.fields.composite import CompositePrimaryKey

from main.activity.models import Activity
from shared.enums import (
    AcquaintancePreference,
    DayOfWeek,
    Gender,
    OrganizingOpenness,
    OtherOption,
    ParticipationGroupKind,
    PersonalityTrait,
    PrivacyScope,
    PrivacySetting,
    SkillLevel,
    TimeOfTheDay,
)

username_validator = RegexValidator(r"^[0-9a-zA-Z_]*$")


class User(AbstractUser):
    username = models.CharField(
        max_length=32, validators=[username_validator], unique=True
    )
    email = models.EmailField(max_length=64, unique=True)
    bio = models.CharField(max_length=512)
    gender = models.SmallIntegerField(choices=Gender.choices(), null=True)
    date_of_birth = models.DateField(null=True)
    longitude = models.FloatField(null=True)
    latitude = models.FloatField(null=True)
    is_capeable = models.BooleanField(default=False)
    first_name = models.CharField(max_length=32)
    last_name = models.CharField(max_length=32)
    xp = models.IntegerField(default=0)
    verified = models.BooleanField(default=False)

    def save(self, *args, **kwargs) -> None:
        if self.username:
            self.username = self.username.lower()
        super().save(*args, **kwargs)

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}" if (self.first_name and self.last_name) else self.username

    @property
    def age(self) -> float:
        return (datetime.date.today() - self.date_of_birth).days / 365

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "main_app_user"


class UserPreferredActivity(models.Model):
    pk = CompositePrimaryKey("preferences", "activity")
    preferences = models.ForeignKey(
        "UserPreferences",
        on_delete=models.CASCADE,
        related_name="preferred_activities",
    )
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    skill_level = models.SmallIntegerField(choices=SkillLevel.choices())

    class Meta:
        db_table = "main_app_preferredactivity"


class UserPreferences(models.Model):
    """Survey answers used for matchmaking. One row per user, created lazily."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="preferences"
    )
    # Q2 — How long should a typical session be? (minutes)
    preferred_session_duration = models.SmallIntegerField(null=True)
    # Q3 — Are you open to organizing events?
    organizing_openness = models.SmallIntegerField(
        choices=OrganizingOpenness.choices(), null=True
    )
    # Q4 — I often take on the role of leader in group activities (1-5)
    leadership_inclination = models.SmallIntegerField(null=True)
    # Q6 — How far are you willing to travel? (km)
    max_travel_distance = models.SmallIntegerField(null=True)
    # Q7 — How often do you want to be active per week? (1-7)
    weekly_activity_target = models.SmallIntegerField(null=True)
    # Q9 — I push through discomfort to improve (1-5)
    pushes_through_discomfort = models.SmallIntegerField(null=True)
    # Q10 — What is your preferred group size? (1-10)
    preferred_group_size = models.SmallIntegerField(null=True)
    # Q12 — I like going to events where I know ...
    acquaintance_preference = models.SmallIntegerField(
        choices=AcquaintancePreference.choices(), null=True
    )
    # Q14 — I enjoy meeting new people (1-5)
    enjoys_meeting_new_people = models.SmallIntegerField(null=True)
    # Q15 — What matters more: the activity itself (1) vs being with people (5)
    activity_vs_social = models.SmallIntegerField(null=True)
    # Q17 — I am additionally motivated by a competitive teammate (1-5)
    motivated_by_competition = models.SmallIntegerField(null=True)
    # Q18 — How far ahead do you need plans set? (1-5)
    planning_horizon = models.SmallIntegerField(null=True)
    # Q19 — I often feel like a burden to my teammate (1-5)
    feels_like_burden = models.SmallIntegerField(null=True)

    class Meta:
        db_table = "main_app_userpreferences"


class UserAvailability(models.Model):
    """Q5 — weekly free time slots, one row per (day, time-of-day) pick."""

    pk = CompositePrimaryKey("preferences", "day_of_week", "time_of_day")
    preferences = models.ForeignKey(
        UserPreferences, on_delete=models.CASCADE, related_name="availabilities"
    )
    day_of_week = models.SmallIntegerField(choices=DayOfWeek.choices())
    time_of_day = models.SmallIntegerField(choices=TimeOfTheDay.choices())

    class Meta:
        db_table = "main_app_useravailability"


class UserParticipationGroup(models.Model):
    """Q11 — groups the user is willing to do activities with."""

    pk = CompositePrimaryKey("preferences", "group_kind")
    preferences = models.ForeignKey(
        UserPreferences,
        on_delete=models.CASCADE,
        related_name="participation_groups",
    )
    group_kind = models.SmallIntegerField(choices=ParticipationGroupKind.choices())

    class Meta:
        db_table = "main_app_userparticipationgroup"


class UserPersonalityTrait(models.Model):
    pk = CompositePrimaryKey("user", "trait")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    trait = models.SmallIntegerField(choices=PersonalityTrait.choices())
    factor = models.FloatField()

    class Meta:
        db_table = "main_app_userpersonalitytrait"


class UserPrivacySetting(models.Model):
    pk = CompositePrimaryKey("user", "setting")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="privacy_settings"
    )
    setting = models.SmallIntegerField(choices=PrivacySetting.choices())
    scope = models.SmallIntegerField(
        choices=PrivacyScope.choices(), default=PrivacyScope.NOONE
    )

    class Meta:
        db_table = "main_app_userprivacysetting"


class UserOtherOption(models.Model):
    pk = CompositePrimaryKey("user", "option")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    option = models.SmallIntegerField(choices=OtherOption.choices())
    text = models.CharField(max_length=128)

    class Meta:
        db_table = "main_app_userotheroption"


class UserReport(models.Model):
    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
    reported = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reported_by"
    )
    comment = models.CharField(max_length=512, null=True)

    class Meta:
        db_table = "main_app_userreport"
