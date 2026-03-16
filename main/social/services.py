from django.db import IntegrityError
from django.db.models import Q, QuerySet

from main.event.models import Event
from main.notification.services import NotificationService
from main.social.models import Block, Comment, CommentLike, Follow, Post, PostLike
from main.social.validators import validate_comment, validate_post
from main.user.models import User
from shared.enums import MemberRole, NotificationKind
from shared.errors.mu_error import MUError, MUErrorCode


class FollowService:
    @staticmethod
    def _get_user_or_raise(user_id: int) -> User:
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)

    @staticmethod
    def follow(user: User, target_user_id: int) -> Follow:
        if target_user_id == user.id:
            raise MUError(MUErrorCode.CANNOT_TARGET_SELF)

        target = FollowService._get_user_or_raise(target_user_id)

        if BlockService.is_blocked(user, target):
            raise MUError(MUErrorCode.BLOCKED_USER)

        if Follow.objects.filter(follower=user, following=target).exists():
            raise MUError(MUErrorCode.ALREADY_FOLLOWING)

        follow = Follow.objects.create(follower=user, following=target)

        NotificationService.send(
            target_user_id, user.id, NotificationKind.NEW_FOLLOWER
        )
        return follow

    @staticmethod
    def unfollow(user: User, target_user_id: int) -> None:
        target = FollowService._get_user_or_raise(target_user_id)

        deleted, _ = Follow.objects.filter(
            follower=user, following=target
        ).delete()
        if not deleted:
            raise MUError(MUErrorCode.NOT_FOLLOWING)

    @staticmethod
    def get_followers(user: User) -> QuerySet[Follow]:
        return Follow.objects.filter(following=user).select_related("follower")

    @staticmethod
    def get_following(user: User) -> QuerySet[Follow]:
        return Follow.objects.filter(follower=user).select_related("following")

    @staticmethod
    def are_mutual(user: User, other: User) -> bool:
        return (
            Follow.objects.filter(follower=user, following=other).exists()
            and Follow.objects.filter(follower=other, following=user).exists()
        )


class BlockService:
    @staticmethod
    def _get_user_or_raise(user_id: int) -> User:
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)

    @staticmethod
    def block_user(user: User, target_user_id: int) -> Block:
        if target_user_id == user.id:
            raise MUError(MUErrorCode.CANNOT_TARGET_SELF)

        target = BlockService._get_user_or_raise(target_user_id)

        if Block.objects.filter(blocker=user, blocked=target).exists():
            raise MUError(MUErrorCode.BLOCKED_USER)

        # Remove follows in both directions
        Follow.objects.filter(
            Q(follower=user, following=target)
            | Q(follower=target, following=user)
        ).delete()

        return Block.objects.create(blocker=user, blocked=target)

    @staticmethod
    def unblock_user(user: User, target_user_id: int) -> None:
        target = BlockService._get_user_or_raise(target_user_id)

        deleted, _ = Block.objects.filter(blocker=user, blocked=target).delete()
        if not deleted:
            raise MUError(MUErrorCode.NOT_BLOCKED)

    @staticmethod
    def is_blocked(user: User, other: User) -> bool:
        return Block.objects.filter(
            Q(blocker=user, blocked=other) | Q(blocker=other, blocked=user)
        ).exists()


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
