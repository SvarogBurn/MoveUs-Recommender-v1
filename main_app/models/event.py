from django.db import models
from django.db.models.fields.composite import CompositePrimaryKey

from .location import Location
from .enums import SkillLevel, MemberRole, EventRating
from .user import MoveusUser
from .activities import Activity

class Event(models.Model):
    title = models.CharField(max_length=64)
    description = models.CharField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.ForeignKey(Location, on_delete=models.DO_NOTHING)
    img_url = models.URLField(default="default.png")
    requirements = models.JSONField(null=True)
    chat = models.ForeignKey('Chat', on_delete=models.DO_NOTHING, null=True)

class EventActivity(models.Model):
    pk = CompositePrimaryKey('event', 'activity')
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    skill_level = models.SmallIntegerField(choices=SkillLevel.choices())

class EventMember(models.Model):
    pk = CompositePrimaryKey('user', 'event')
    user = models.ForeignKey(MoveusUser, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    # likes = models.ManyToManyField(MoveusUser, related_name='liked_on_event_by') Does not work trenutno
    role = models.SmallIntegerField(choices=MemberRole.choices())
    has_participated = True
    score = models.SmallIntegerField(choices=EventRating.choices())
    comment = models.CharField(max_length=512)