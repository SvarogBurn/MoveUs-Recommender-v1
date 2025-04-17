from django.db import models
from django.db.models.fields.composite import CompositePrimaryKey

from .location import Location
from .enums import SkillLevel, MemberRole, EventRating
from .activities import Activity

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

    def participant_count(self):
        return EventMember.objects.filter(
            event_id = self.id,
            role = MemberRole.PARTICIPANT
        ).count()

class EventMember(models.Model):
    pk = CompositePrimaryKey('user', 'event')
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    event = models.ForeignKey("Event", on_delete=models.CASCADE, related_name="members")
    # likes = models.ManyToManyField(User, related_name='liked_on_event_by') Does not work :<<
    role = models.SmallIntegerField(choices=MemberRole.choices())
    has_participated = models.BooleanField(default=False)
    score = models.SmallIntegerField(choices=EventRating.choices(), null=True)
    comment = models.CharField(max_length=512, null=True)