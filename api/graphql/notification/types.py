import graphene

from api.graphql.event.types import EventType
from api.graphql.user.types import UserType
from shared.enums import NotificationKind


class BaseNotificationType(graphene.Interface):
    id = graphene.Int()
    notification_type = NotificationKind.as_graphene_enum()()
    time = graphene.DateTime()


class UserNotificationType(graphene.ObjectType):
    class Meta:
        interfaces = (BaseNotificationType,)

    user = graphene.Field(UserType)


class EventNotificationType(graphene.ObjectType):
    class Meta:
        interfaces = (BaseNotificationType,)

    event = graphene.Field(EventType)
