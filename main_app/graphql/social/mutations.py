import graphene
from graphql import GraphQLError

from django.db.models import Q

from ...models import Relationship, MoveusUser
from ...models.enums import RelationshipStatus

from .types import RelationshipType

class SendFriendRequestMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @classmethod
    def mutate(cls, root, info, user_id):
        if not info.context.user.id: raise GraphQLError("Not authentificated")

        if user_id == info.context.user.id: raise GraphQLError("Cannot send request to yourself")

        other =  MoveusUser.objects.get(pk=user_id)

        q_1 = Q(user_1 = info.context.user, user_2 = other)
        q_2 = Q(user_2 = info.context.user, user_1 = other)

        try:
            existing_relationship = Relationship.objects.get(q_1 | q_2)
            if existing_relationship and existing_relationship.status != RelationshipStatus.NONE: raise GraphQLError("Cannot send friend request to this user")
            existing_relationship.user_1 = info.context.user
            existing_relationship.user_2  = other
            existing_relationship.status = RelationshipStatus.PENDING
            existing_relationship.save()
            return SendFriendRequestMutation(relationship = existing_relationship)
        
        except Relationship.DoesNotExist:
            new_relationship = Relationship.objects.create(user_1 = info.context.user, user_2 = other, status = RelationshipStatus.PENDING)
            return SendFriendRequestMutation(relationship = new_relationship)
        
class AcceptFriendRequestMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @classmethod
    def mutate(cls, root, info, user_id):
        if not info.context.user.id: raise GraphQLError("Not authentificated")

        other =  MoveusUser.objects.get(pk=user_id)

        try:
            existing_relationship = Relationship.objects.get(user_1 = other, user_2 = info.context.user)
            if existing_relationship.status != RelationshipStatus.PENDING: raise GraphQLError("No request to accept")

            existing_relationship.status = RelationshipStatus.FRIENDS;
            existing_relationship.save()
            return AcceptFriendRequestMutation(relationship = existing_relationship)
        except Relationship.DoesNotExist:
            raise GraphQLError("No request to accept")

class CancelFriendRequestMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @classmethod
    def mutate(cls, root, info, user_id):
        if not info.context.user.id: raise GraphQLError("Not authentificated")

        other =  MoveusUser.objects.get(pk=user_id)

        try:
            existing_relationship = Relationship.objects.get(user_1 = info.context.user, user_2 = other)
            if existing_relationship.status != RelationshipStatus.PENDING: raise GraphQLError("No request to cancel")

            existing_relationship.status = RelationshipStatus.NONE;
            existing_relationship.save()

            return CancelFriendRequestMutation(relationship = existing_relationship)
        except Relationship.DoesNotExist:
            raise GraphQLError("No request to cancel")

class RejectFriendRequestMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @classmethod
    def mutate(cls, root, info, user_id):
        if not info.context.user.id: raise GraphQLError("Not authentificated")

        other =  MoveusUser.objects.get(pk=user_id)

        try:
            existing_relationship = Relationship.objects.get(user_1 = other, user_2 = info.context.user)
            if existing_relationship.status != RelationshipStatus.PENDING: raise GraphQLError("No request to reject")

            existing_relationship.status = RelationshipStatus.NONE;
            existing_relationship.save()
            return AcceptFriendRequestMutation(relationship = existing_relationship)
        except Relationship.DoesNotExist:
            raise GraphQLError("No request to reject")

class Mutation(graphene.ObjectType):
    send_friend_request = SendFriendRequestMutation.Field()
    accept_friend_request = AcceptFriendRequestMutation.Field()
    cancel_friend_request = CancelFriendRequestMutation.Field()
    reject_friends_request = RejectFriendRequestMutation.Field()
