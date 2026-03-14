from django.db import IntegrityError
from django.db.models import Q, QuerySet

from main.chat.services import ChatService
from main.event.models import Event
from main.notification.services import NotificationService
from main.social.models import Comment, CommentLike, Post, PostLike, Relationship
from main.social.validators import validate_comment, validate_post
from main.user.models import User
from shared.enums import MemberRole, NotificationEnum, RelationshipStatus
from shared.errors.mu_error import MUError, MUErrorCode


class RelationshipService:
    @staticmethod
    def get_or_create(user: User, target_user: User) -> Relationship:
        q1 = Q(user_1=user, user_2=target_user)
        q2 = Q(user_2=user, user_1=target_user)
        try:
            return Relationship.objects.get(q1 | q2)
        except Relationship.DoesNotExist:
            relationship = Relationship.objects.create(
                user_1=user, user_2=target_user, status=RelationshipStatus.NONE
            )
            relationship.refresh_from_db()
            return relationship
        
    @staticmethod
    def get_requests_sent(user: User) -> QuerySet[Relationship]:
        return Relationship.objects.filter(
            user_1=user, status=RelationshipStatus.PENDING
        )

    @staticmethod
    def get_requests_pending(user: User) -> QuerySet[Relationship]:
        return Relationship.objects.filter(
            user_2=user, status=RelationshipStatus.PENDING
        )

    @staticmethod
    def get_friends(user: User) -> QuerySet[Relationship]:
        q1 = Q(user_1=user)
        q2 = Q(user_2=user)
        return Relationship.objects.filter(q1 | q2, status=RelationshipStatus.FRIENDS)

    @staticmethod
    def _get_user_or_raise(user_id: int) -> User:
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)

    @staticmethod
    def send_friend_request(from_user: User, to_user_id: int) -> Relationship:
        if to_user_id == from_user.id:
            raise MUError(MUErrorCode.CANNOT_HAVE_RELATION_WITH_SELF)

        other = RelationshipService._get_user_or_raise(to_user_id)

        q_1 = Q(user_1=from_user, user_2=other)
        q_2 = Q(user_2=from_user, user_1=other)

        try:
            relationship = Relationship.objects.get(q_1 | q_2)
            if relationship.status != RelationshipStatus.NONE:
                raise MUError(MUErrorCode.INVALID_FRIEND_REQUEST)

            relationship.status = RelationshipStatus.PENDING
            relationship.save()

            if relationship.user_1 != from_user:
                relationship.swap_users()

        except Relationship.DoesNotExist:
            relationship = Relationship.objects.create(
                user_1=from_user, user_2=other, status=RelationshipStatus.PENDING
            )

        NotificationService.send(
            to_user_id, from_user.id, NotificationEnum.FRIEND_REQUEST
        )
        return relationship

    @staticmethod
    def accept_friend_request(accepting_user: User, from_user_id: int) -> Relationship:
        other = RelationshipService._get_user_or_raise(from_user_id)

        try:
            relationship = Relationship.objects.get(user_1=other, user_2=accepting_user)
            if relationship.status != RelationshipStatus.PENDING:
                raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

            relationship.status = RelationshipStatus.FRIENDS
            relationship.save()

            ChatService.create_chat_for_relationship(relationship)

            NotificationService.send(
                from_user_id, accepting_user.id, NotificationEnum.FRIEND_ACCEPTED
            )
            return relationship
        except Relationship.DoesNotExist:
            raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

    @staticmethod
    def cancel_friend_request(from_user: User, to_user_id: int) -> Relationship:
        other = RelationshipService._get_user_or_raise(to_user_id)

        try:
            relationship = Relationship.objects.get(user_1=from_user, user_2=other)
            if relationship.status != RelationshipStatus.PENDING:
                raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

            relationship.status = RelationshipStatus.NONE
            relationship.save()
            return relationship
        except Relationship.DoesNotExist:
            raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

    @staticmethod
    def reject_friend_request(rejecting_user: User, from_user_id: int) -> Relationship:
        other = RelationshipService._get_user_or_raise(from_user_id)

        try:
            relationship = Relationship.objects.get(user_1=other, user_2=rejecting_user)
            if relationship.status != RelationshipStatus.PENDING:
                raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

            relationship.status = RelationshipStatus.NONE
            relationship.save()
            return relationship
        except Relationship.DoesNotExist:
            raise MUError(MUErrorCode.FRIEND_REQUEST_DOES_NOT_EXIST)

    @staticmethod
    def remove_friend(user: User, other_user_id: int) -> Relationship:
        other = RelationshipService._get_user_or_raise(other_user_id)

        q_1 = Q(user_1=user, user_2=other)
        q_2 = Q(user_2=user, user_1=other)

        try:
            relationship = Relationship.objects.get(q_1 | q_2)
            if relationship.status != RelationshipStatus.FRIENDS:
                raise MUError(MUErrorCode.NOT_FRIENDS)

            relationship.status = RelationshipStatus.NONE
            relationship.save()
            return relationship
        except Relationship.DoesNotExist:
            raise MUError(MUErrorCode.NOT_FRIENDS)

    @staticmethod
    def block_user(blocking_user: User, target_user_id: int) -> Relationship:
        if target_user_id == blocking_user.id:
            raise MUError(MUErrorCode.CANNOT_HAVE_RELATION_WITH_SELF)

        other = RelationshipService._get_user_or_raise(target_user_id)

        q_1 = Q(user_1=blocking_user, user_2=other)
        q_2 = Q(user_2=blocking_user, user_1=other)

        try:
            relationship = Relationship.objects.get(q_1 | q_2)

            if relationship.is_blocked(blocking_user.id):
                relationship.status = RelationshipStatus.BLOCKED_BY_BOTH
            else:
                relationship.status = RelationshipStatus.BLOCKED_BY_ONE
                if blocking_user.id == relationship.user_2_id:
                    relationship.swap_users()

            relationship.save()
            return relationship

        except Relationship.DoesNotExist:
            return Relationship.objects.create(
                user_1=blocking_user,
                user_2=other,
                status=RelationshipStatus.BLOCKED_BY_ONE,
            )

    @staticmethod
    def unblock_user(unblocking_user: User, target_user_id: int) -> Relationship:
        if target_user_id == unblocking_user.id:
            raise MUError(MUErrorCode.CANNOT_HAVE_RELATION_WITH_SELF)

        other = RelationshipService._get_user_or_raise(target_user_id)

        q_1 = Q(user_1=unblocking_user, user_2=other)
        q_2 = Q(user_2=unblocking_user, user_1=other)

        try:
            relationship = Relationship.objects.get(q_1 | q_2)

            if relationship.is_blocked(target_user_id):
                if relationship.status == RelationshipStatus.BLOCKED_BY_BOTH:
                    relationship.status = RelationshipStatus.BLOCKED_BY_ONE
                    if unblocking_user.id == relationship.user_1_id:
                        relationship.swap_users()
                else:
                    relationship.status = RelationshipStatus.NONE

            relationship.save()
            return relationship

        except Relationship.DoesNotExist:
            raise MUError(MUErrorCode.NOT_FRIENDS)


class PostService:
    @staticmethod
    def create_post(user: User, content: str, event_id: int | None = None) -> Post:
        validate_post(content)

        if event_id is not None:
            from main.event.services import EventService

            EventService.get_event(event_id, user.id, MemberRole.MODERATOR)

        return Post.objects.create(content=content, author=user, event_id=event_id)

    @staticmethod
    def like_post(user: User, post_id: int) -> None:
        try:
            post = Post.objects.get(pk=post_id)
        except Post.DoesNotExist:
            raise MUError(MUErrorCode.POST_DOES_NOT_EXIST)
        post.liked_by.add(user)

    @staticmethod
    def unlike_post(user: User, post_id: int) -> None:
        try:
            post = Post.objects.get(pk=post_id)
        except Post.DoesNotExist:
            raise MUError(MUErrorCode.POST_DOES_NOT_EXIST)
        post.liked_by.remove(user)


class CommentService:
    @staticmethod
    def comment_on_post(user: User, post_id: int, text: str) -> Comment:
        validate_comment(text)
        try:
            Post.objects.get(pk=post_id)
        except Post.DoesNotExist:
            raise MUError(MUErrorCode.POST_DOES_NOT_EXIST)
        return Comment.objects.create(user=user, post_id=post_id, text=text)

    @staticmethod
    def comment_on_event(user: User, event_id: int, text: str) -> Comment:
        validate_comment(text)
        try:
            Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            raise MUError(MUErrorCode.EVENT_DOES_NOT_EXIST)
        return Comment.objects.create(user=user, event_id=event_id, text=text)

    @staticmethod
    def reply_to_comment(user: User, comment_id: int, text: str) -> Comment:
        validate_comment(text)
        try:
            parent = Comment.objects.get(pk=comment_id)
        except Comment.DoesNotExist:
            raise MUError(MUErrorCode.COMMENT_DOES_NOT_EXIST)

        if parent.parent is not None:
            raise MUError(MUErrorCode.COMMENT_NESTING_TOO_DEEP)

        return Comment.objects.create(
            user=user,
            text=text,
            parent=parent,
            post_id=parent.post_id,
            event_id=parent.event_id,
        )

    @staticmethod
    def like_comment(user: User, comment_id: int) -> None:
        try:
            Comment.objects.get(pk=comment_id)
        except Comment.DoesNotExist:
            raise MUError(MUErrorCode.COMMENT_DOES_NOT_EXIST)
        try:
            CommentLike.objects.create(comment_id=comment_id, user=user)
        except IntegrityError:
            pass

    @staticmethod
    def unlike_comment(user: User, comment_id: int) -> None:
        try:
            Comment.objects.get(pk=comment_id)
        except Comment.DoesNotExist:
            raise MUError(MUErrorCode.COMMENT_DOES_NOT_EXIST)
        CommentLike.objects.filter(comment_id=comment_id, user=user).delete()

    @staticmethod
    def get_comments_for_post(post: Post, start: int, end: int) -> QuerySet[Comment]:
        return (
            Comment.objects.filter(post=post, parent__isnull=True)
            .order_by("-time_posted")[start:end]
        )

    @staticmethod
    def get_comments_for_event(
        event: Event, start: int, end: int
    ) -> QuerySet[Comment]:
        return (
            Comment.objects.filter(event=event, parent__isnull=True)
            .order_by("-time_posted")[start:end]
        )
