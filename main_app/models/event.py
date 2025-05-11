from functools import cached_property

from django.db import models
from django.db.models.fields.composite import CompositePrimaryKey
from django.utils.timezone import now

from .activities import Activity
from .enums import EventRating, MemberRole, SkillLevel


class Event(models.Model):
    title = models.CharField(max_length=32)
    description = models.CharField(max_length=1024, null = True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.ForeignKey("Location", on_delete=models.DO_NOTHING)
    requirements = models.JSONField(null=True)
    chat = models.ForeignKey('Chat', on_delete=models.DO_NOTHING, null=True)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    skill_level = models.SmallIntegerField(choices=SkillLevel.choices())
    max_participants = models.IntegerField(null=True)
    allow_spectators = models.BooleanField(default=False)
    min_age = models.SmallIntegerField(null=True)
    max_age = models.SmallIntegerField(null=True)
    accepted_genders = models.JSONField(null=True)
    finished = models.BooleanField(default=False)

    def participant_count(self):
        return EventMember.objects.filter(
            event_id = self.id,
            participates = True
        ).count()

class EventMember(models.Model):
    pk = CompositePrimaryKey('user', 'event')
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    event = models.ForeignKey("Event", on_delete=models.CASCADE, related_name="members")
    role = models.SmallIntegerField(choices=MemberRole.choices())
    has_participated = models.BooleanField(null=True)
    score = models.SmallIntegerField(choices=EventRating.choices(), null=True)
    comment = models.CharField(max_length=512, null=True)
    participates = models.BooleanField(default=role==MemberRole.PARTICIPANT)

class EventMemberLike(models.Model):
    pk = CompositePrimaryKey('event', 'user_1', 'user_2')
    event = models.ForeignKey("Event", on_delete=models.CASCADE)
    user_1 = models.ForeignKey("User", on_delete=models.CASCADE, related_name='likes')
    user_2 = models.ForeignKey("User", on_delete=models.CASCADE, related_name='liked_by')
    like = models.BooleanField(default=True)