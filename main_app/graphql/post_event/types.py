import graphene

from main_app.graphql.event_member.types import EventMemberType

class EventCommentType(graphene.ObjectType):
    member = graphene.Field(EventMemberType)
    comment = graphene.String()