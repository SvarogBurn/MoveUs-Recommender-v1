import graphene

from main_app.graphql.event.types import EventType
from main_app.graphql.user.types import UserType
from main_app.models.enums import NotificationEnum


class BaseNotificationType(graphene.Interface):
    id = graphene.Int()
    notification_type = NotificationEnum.as_graphene_enum()()
    time = graphene.DateTime()

class UserNotificationType(graphene.ObjectType):
    class Meta:
        interfaces = (BaseNotificationType, )

    user = graphene.Field(UserType)

class EventNotificationType(graphene.ObjectType):
    class Meta:
        interfaces = (BaseNotificationType, )

    event = graphene.Field(EventType)