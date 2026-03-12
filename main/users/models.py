import datetime

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.fields.composite import CompositePrimaryKey

from main.activities.models import Activity
from shared.enums import (
    FrequencyOfPhycicalActivity,
    Gender,
    MainInterest,
    MatchedParticipationLikelihood,
    OtherOption,
    PersonalityTrait,
    PhysicalActivitySatisfaction,
    PreferredPartySize,
    PrivacyScope,
    PrivacySetting,
    SkillLevel,
    SocialInteractionImportance,
)

username_validator = RegexValidator(r"^[0-9a-zA-Z_]*$")


class User(AbstractUser):
    username = models.CharField(
        max_length=32, validators=[username_validator], unique=True
    )
    email = models.EmailField(max_length=64, unique=True)
    bio = models.CharField(max_length=255)
    gender = models.SmallIntegerField(choices=Gender.choices(), null=True)
    date_of_birth = models.DateField(null=True)
    longitude = models.FloatField(null=True)
    latitude = models.FloatField(null=True)
    frequency_of_physical_activity = models.SmallIntegerField(
        choices=FrequencyOfPhycicalActivity.choices(), null=True
    )
    social_interaction_importance = models.SmallIntegerField(
        choices=SocialInteractionImportance.choices(), null=True
    )
    preferred_party_size = models.SmallIntegerField(
        choices=PreferredPartySize.choices(), null=True
    )
    formed_relationship_types = models.JSONField(null=True)
    physical_activity_satisfaction = models.SmallIntegerField(
        choices=PhysicalActivitySatisfaction.choices(), null=True
    )
    preferred_partner_characteristics = models.JSONField(null=True)
    matched_participation_likelihood = models.SmallIntegerField(
        choices=MatchedParticipationLikelihood.choices(), null=True
    )
    preferred_time_of_the_day = models.JSONField(null=True)
    preferred_event_duration = models.SmallIntegerField(null=True)
    gender_preference = models.JSONField(null=True)
    max_travel_distance = models.SmallIntegerField(null=True)
    main_interest = models.SmallIntegerField(choices=MainInterest.choices(), null=True)
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
        return self.first_name if self.first_name else self.username

    @property
    def age(self) -> float:
        return (datetime.date.today() - self.date_of_birth).days / 365

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "main_app_user"


class PreferredActivity(models.Model):
    pk = CompositePrimaryKey("user", "activity")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="preferred_activities"
    )
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    skill_level = models.SmallIntegerField(choices=SkillLevel.choices())

    class Meta:
        db_table = "main_app_preferredactivity"


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
        choices=PrivacyScope.choices(), default=PrivacyScope.EVERYONE
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
