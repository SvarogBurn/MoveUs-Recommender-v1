from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.fields.composite import CompositePrimaryKey

from .location import Location
from .enums import *
from .activities import Activity

class MoveusUser(AbstractUser):
    email = models.EmailField(max_length=64, unique=True)
    bio = models.CharField(max_length=255)
    gender = models.SmallIntegerField(choices=Gender.choices(), null=True)
    date_of_birth = models.DateField(null=True)
    location = models.ForeignKey(Location, on_delete=models.DO_NOTHING, null=True)
    frequency_of_physical_activity = models.SmallIntegerField(choices=FrequencyOfPhycicalActivity.choices(), null=True)
    social_iteraction_importance = models.SmallIntegerField(choices=SocialInteractionImportance.choices(), null=True)
    preferred_party_size = models.SmallIntegerField(choices=PreferredPartySize.choices(), null=True)
    new_friendships_formed = models.BooleanField(null=True)
    formed_relationships_type = models.JSONField(null=True)
    physical_activity_satisfaction = models.SmallIntegerField(choices=PhysicalActivitySatisfaction.choices(), null=True)
    preferred_partned_characteristics = models.JSONField(null=True)
    matched_participation_likelihood = models.SmallIntegerField(choices=MatchedParticipationLikelihood.choices(), null=True)
    is_capeable = models.BooleanField(default=False)
    first_name = models.CharField(max_length=32)
    last_name = models.CharField(max_length=32)
    xp = models.IntegerField(default=0)
    passed_tutorial = models.BooleanField(default=False)
    img_url = models.URLField()
    verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

class PreferredActivity(models.Model):
    pk = CompositePrimaryKey('user', 'activity')
    user = models.ForeignKey(MoveusUser, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    skill_level = models.SmallIntegerField(choices=SkillLevel.choices())