from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.fields.composite import CompositePrimaryKey
from django.core.validators import RegexValidator

from .enums import *

username_validator = RegexValidator(r"^[0-9a-zA-Z_]*$")

class User(AbstractUser):
    username = models.CharField(max_length=32, validators=[username_validator], unique=True)
    email = models.EmailField(max_length=64, unique=True)
    bio = models.CharField(max_length=255)
    gender = models.SmallIntegerField(choices=Gender.choices(), null=True)
    date_of_birth = models.DateField(null=True)
    longitude = models.FloatField(null=True)
    latitude = models.FloatField(null=True)
    frequency_of_physical_activity = models.SmallIntegerField(choices=FrequencyOfPhycicalActivity.choices(), null=True)
    social_interaction_importance = models.SmallIntegerField(choices=SocialInteractionImportance.choices(), null=True)
    preferred_party_size = models.SmallIntegerField(choices=PreferredPartySize.choices(), null=True)
    formed_relationship_types = models.JSONField(null=True)
    physical_activity_satisfaction = models.SmallIntegerField(choices=PhysicalActivitySatisfaction.choices(), null=True)
    preferred_partner_characteristics = models.JSONField(null=True)
    matched_participation_likelihood = models.SmallIntegerField(choices=MatchedParticipationLikelihood.choices(), null=True)
    preferred_time_of_the_day = models.JSONField(null=True)
    is_capeable = models.BooleanField(default=False)
    first_name = models.CharField(max_length=32)
    last_name = models.CharField(max_length=32)
    xp = models.IntegerField(default=0)
    verified = models.BooleanField(default=False)

    @property
    def display_name(self):
        return self.first_name if self.first_name else self.username

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

class PreferredActivity(models.Model):
    pk = CompositePrimaryKey('user', 'activity')
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="preferred_activities")
    activity = models.ForeignKey("Activity", on_delete=models.CASCADE)
    skill_level = models.SmallIntegerField(choices=SkillLevel.choices())