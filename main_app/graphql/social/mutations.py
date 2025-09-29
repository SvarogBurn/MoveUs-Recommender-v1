import graphene
from django.db.models import Q

from main_app.util import require_auth, send_notification

from ..error import MUError, MUErrorCode
from ...models import Relationship, User
from ...models.enums import RelationshipStatus, NotificationEnum

from .types import RelationshipType

class SendFriendRequestMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @require_auth
    def mutate(self, info, user_id):
        if user_id == info.context.user.id: raise MUError(MUErrorCode.CANNOT_HAVE_RELATION_WITH_SELF)

        other = User.objects.get(pk=user_id)

        q_1 = Q(user_1 = info.context.user, user_2 = other)
        q_2 = Q(user_2 = info.context.user, user_1 = other)

        try:
            existing_relationship = Relationship.objects.get(q_1 | q_2)
            if existing_relationship and existing_relationship.status != RelationshipStatus.NONE: raise MUError(MUErrorCode.INVALID_FRIEND_REQUEST)
            
            existing_relationship.status = RelationshipStatus.PENDING
            existing_relationship.save()

            if existing_relationship.user_1 != info.context.user:
                existing_relationship.swap_users()
            
            send_notification(user_id, info.context.user.id, NotificationEnum.FRIEND_REQUEST)
            return SendFriendRequestMutation(relationship = existing_relationship)
        
        except Relationship.DoesNotExist:
            send_notification(user_id, info.context.user.id, NotificationEnum.FRIEND_REQUEST)
            new_relationship = Relationship.objects.create(user_1 = info.context.user, user_2 = other, status = RelationshipStatus.PENDING)
            return SendFriendRequestMutation(relationship = new_relationship)
        
class AcceptFriendRequestMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @require_auth
    def mutate(self, info, user_id):
        other =  User.objects.get(pk=user_id)

        try:
            existing_relationship = Relationship.objects.get(user_1 = other, user_2 = info.context.user)
            if existing_relationship.status != RelationshipStatus.PENDING: raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

            existing_relationship.status = RelationshipStatus.FRIENDS
            existing_relationship.save()
            send_notification(user_id, info.context.user.id, NotificationEnum.FRIEND_ACCEPTED)
            return AcceptFriendRequestMutation(relationship = existing_relationship)
        except Relationship.DoesNotExist:
            raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

class CancelFriendRequestMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @require_auth
    def mutate(self, info, user_id):
        other =  User.objects.get(pk=user_id)

        try:
            existing_relationship = Relationship.objects.get(user_1 = info.context.user, user_2 = other)
            if existing_relationship.status != RelationshipStatus.PENDING: raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

            existing_relationship.status = RelationshipStatus.NONE
            existing_relationship.save()

            return CancelFriendRequestMutation(relationship = existing_relationship)
        except Relationship.DoesNotExist:
            raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

class RejectFriendRequestMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @require_auth
    def mutate(self, info, user_id):
        other =  User.objects.get(pk=user_id)

        try:
            existing_relationship = Relationship.objects.get(user_1 = other, user_2 = info.context.user)
            if existing_relationship.status != RelationshipStatus.PENDING: raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

            existing_relationship.status = RelationshipStatus.NONE
            existing_relationship.save()
            return AcceptFriendRequestMutation(relationship = existing_relationship)
        except Relationship.DoesNotExist:
            raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

class RemoveFriendMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @require_auth
    def mutate(self, info, user_id):
        other =  User.objects.get(pk=user_id)

        try:
            existing_relationship = Relationship.objects.get(user_1 = other, user_2 = info.context.user)
            if existing_relationship.status != RelationshipStatus.FRIENDS: raise MUError(MUErrorCode.NOT_FRIENDS)

            existing_relationship.status = RelationshipStatus.NONE
            existing_relationship.save()
            return RemoveFriendMutation(relationship = existing_relationship)
        except Relationship.DoesNotExist:
            raise MUError(MUErrorCode.NOT_FRIENDS)
        
class BlockUserMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @require_auth
    def mutate(self, info, user_id):
        if user_id == info.context.user.id: raise MUError(MUErrorCode.CANNOT_HAVE_RELATION_WITH_SELF)

        other = User.objects.get(pk=user_id)

        q_1 = Q(user_1 = info.context.user, user_2 = other)
        q_2 = Q(user_2 = info.context.user, user_1 = other)

        try:
            existing_relationship = Relationship.objects.get(q_1 | q_2)
            
            if existing_relationship.is_blocked(info.context.user.id):
                existing_relationship.status = RelationshipStatus.BLOCKED_BY_BOTH
            else:
                existing_relationship.status = RelationshipStatus.BLOCKED_BY_ONE
                if info.context.user.id == existing_relationship.user_2_id:
                    existing_relationship.swap_users()

            existing_relationship.save()
            return BlockUserMutation(relationship = existing_relationship)
        
        except Relationship.DoesNotExist:
            Relationship.objects.create(user_1 = info.context.user, user_2 = other, status = RelationshipStatus.BLOCKED_BY_ONE)
            return BlockUserMutation(relationship = existing_relationship)

class UnblockUserMutation(graphene.Mutation):

    class Arguments:
        user_id = graphene.Int()

    relationship = graphene.Field(RelationshipType)

    @require_auth
    def mutate(cls, root, info, user_id):
        if user_id == info.context.user.id: raise MUError(MUErrorCode.CANNOT_HAVE_RELATION_WITH_SELF)

        other = User.objects.get(pk=user_id)

        q_1 = Q(user_1 = info.context.user, user_2 = other)
        q_2 = Q(user_2 = info.context.user, user_1 = other)

        try:
            existing_relationship = Relationship.objects.get(q_1 | q_2)
            
            if existing_relationship.is_blocked(user_id):

                if existing_relationship.status == RelationshipStatus.BLOCKED_BY_BOTH:
                    existing_relationship.status = RelationshipStatus.BLOCKED_BY_ONE
                    if info.context.user.id == existing_relationship.user_1_id:
                        existing_relationship.swap_users()
                
                else:
                    existing_relationship.status = None

            existing_relationship.save()
            return UnblockUserMutation(relationship = existing_relationship)
        
        except Relationship.DoesNotExist:
            return UnblockUserMutation(relationship = existing_relationship)

class Mutation(graphene.ObjectType):
    send_friend_request = SendFriendRequestMutation.Field()
    accept_friend_request = AcceptFriendRequestMutation.Field()
    cancel_friend_request = CancelFriendRequestMutation.Field()
    reject_friend_request = RejectFriendRequestMutation.Field()
    remove_friend = RemoveFriendMutation.Field()
