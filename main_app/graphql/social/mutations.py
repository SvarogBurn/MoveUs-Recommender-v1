import graphene

from django.db.models import Q

from ..error import MUError, MUErrorCode
from ...models import Relationship, User
from ...models.enums import RelationshipStatus

from .types import RelationshipType

class SendFriendRequestMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @classmethod
    def mutate(cls, root, info, user_id):
        if not info.context.user.id: raise MUError(MUErrorCode.AUTHENTIFICATION_ERROR)

        if user_id == info.context.user.id: raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

        other =  User.objects.get(pk=user_id)

        q_1 = Q(user_1 = info.context.user, user_2 = other)
        q_2 = Q(user_2 = info.context.user, user_1 = other)

        try:
            existing_relationship = Relationship.objects.get(q_1 | q_2)
            if existing_relationship and existing_relationship.status != RelationshipStatus.NONE: raise MUError(MUErrorCode.INVALID_FRIEND_REQUEST)
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
        if not info.context.user.id: raise MUError(MUErrorCode.AUTHENTIFICATION_ERROR)

        other =  User.objects.get(pk=user_id)

        try:
            existing_relationship = Relationship.objects.get(user_1 = other, user_2 = info.context.user)
            if existing_relationship.status != RelationshipStatus.PENDING: raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

            existing_relationship.status = RelationshipStatus.FRIENDS;
            existing_relationship.save()
            return AcceptFriendRequestMutation(relationship = existing_relationship)
        except Relationship.DoesNotExist:
            raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

class CancelFriendRequestMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @classmethod
    def mutate(cls, root, info, user_id):
        if not info.context.user.id: raise MUError(MUErrorCode.AUTHENTIFICATION_ERROR)

        other =  User.objects.get(pk=user_id)

        try:
            existing_relationship = Relationship.objects.get(user_1 = info.context.user, user_2 = other)
            if existing_relationship.status != RelationshipStatus.PENDING: raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

            existing_relationship.status = RelationshipStatus.NONE;
            existing_relationship.save()

            return CancelFriendRequestMutation(relationship = existing_relationship)
        except Relationship.DoesNotExist:
            raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

class RejectFriendRequestMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @classmethod
    def mutate(cls, root, info, user_id):
        if not info.context.user.id: raise MUError(MUErrorCode.AUTHENTIFICATION_ERROR)

        other =  User.objects.get(pk=user_id)

        try:
            existing_relationship = Relationship.objects.get(user_1 = other, user_2 = info.context.user)
            if existing_relationship.status != RelationshipStatus.PENDING: raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

            existing_relationship.status = RelationshipStatus.NONE;
            existing_relationship.save()
            return AcceptFriendRequestMutation(relationship = existing_relationship)
        except Relationship.DoesNotExist:
            raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

class Mutation(graphene.ObjectType):
    send_friend_request = SendFriendRequestMutation.Field()
    accept_friend_request = AcceptFriendRequestMutation.Field()
    cancel_friend_request = CancelFriendRequestMutation.Field()
    reject_friends_request = RejectFriendRequestMutation.Field()
