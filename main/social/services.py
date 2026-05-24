from django.db.models import Count, Exists, OuterRef, Q, QuerySet

from main.event.models import Event
from main.notification.services import NotificationService
from main.social.models import Block, Comment, CommentLike, Follow, Post, PostLike
from main.social.validators import (
    validate_comment_length,
    validate_comment_nesting,
    validate_not_self,
    validate_post,
)
from main.user.models import User
from shared.enums import MemberRole, NotificationKind
from shared.errors.mu_error import MUError, MUErrorCode


def _annotate_posts(qs: QuerySet[Post], user_id: int | None) -> QuerySet[Post]:
    qs = qs.annotate(_like_count=Count("postlike__user", distinct=True))
    if user_id:
        qs = qs.annotate(
            _is_liked=Exists(
                PostLike.objects.filter(post_id=OuterRef("pk"), user_id=user_id)
            )
        )
    return qs


def _annotate_comments(
    qs: QuerySet[Comment], user_id: int | None
) -> QuerySet[Comment]:
    qs = qs.annotate(_like_count=Count("commentlike__user", distinct=True))
    if user_id:
        qs = qs.annotate(
            _is_liked=Exists(
                CommentLike.objects.filter(
                    comment_id=OuterRef("pk"), user_id=user_id
                )
            )
        )
    return qs


class FollowService:
    @staticmethod
    def _get_user_or_raise(user_id: int) -> User:
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)

    @staticmethod
    def follow(user_id: int, target_user_id: int) -> Follow:
        validate_not_self(user_id, target_user_id)

        FollowService._get_user_or_raise(target_user_id)

        if BlockService.is_blocked(user_id, target_user_id):
            raise MUError(MUErrorCode.BLOCKED_USER)

        if Follow.objects.filter(
            follower_id=user_id, following_id=target_user_id
        ).exists():
            raise MUError(MUErrorCode.ALREADY_FOLLOWING)

        follow = Follow.objects.create(
            follower_id=user_id, following_id=target_user_id
        )

        NotificationService.send(
            target_user_id, user_id, NotificationKind.NEW_FOLLOWER
        )
        return follow

    @staticmethod
    def unfollow(user_id: int, target_user_id: int) -> None:
        FollowService._get_user_or_raise(target_user_id)

        deleted, _ = Follow.objects.filter(
            follower_id=user_id, following_id=target_user_id
        ).delete()
        if not deleted:
            raise MUError(MUErrorCode.NOT_FOLLOWING)

    @staticmethod
    def get_followers(user_id: int) -> QuerySet[Follow]:
        return Follow.objects.filter(following_id=user_id).select_related("follower")

    @staticmethod
    def get_following(user_id: int) -> QuerySet[Follow]:
        return Follow.objects.filter(follower_id=user_id).select_related("following")

    @staticmethod
    def are_mutual(user_id: int, other_id: int) -> bool:
        return (
            Follow.objects.filter(
                follower_id=user_id, following_id=other_id
            ).exists()
            and Follow.objects.filter(
                follower_id=other_id, following_id=user_id
            ).exists()
        )

    @staticmethod
    def is_following(follower_id: int, following_id: int) -> bool:
        return Follow.objects.filter(
            follower_id=follower_id, following_id=following_id
        ).exists()

    @staticmethod
    def get_follower_users(user_id: int) -> list[User]:
        follows = FollowService.get_followers(user_id)
        return [f.follower for f in follows]

    @staticmethod
    def get_following_users(user_id: int) -> list[User]:
        follows = FollowService.get_following(user_id)
        return [f.following for f in follows]

    @staticmethod
    def get_follower_count(user_id: int) -> int:
        return FollowService.get_followers(user_id).count()

    @staticmethod
    def get_following_count(user_id: int) -> int:
        return FollowService.get_following(user_id).count()


class BlockService:
    @staticmethod
    def _get_user_or_raise(user_id: int) -> User:
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)

    @staticmethod
    def block_user(user_id: int, target_user_id: int) -> Block:
        validate_not_self(user_id, target_user_id)

        BlockService._get_user_or_raise(target_user_id)

        if Block.objects.filter(
            blocker_id=user_id, blocked_id=target_user_id
        ).exists():
            raise MUError(MUErrorCode.BLOCKED_USER)

        # Remove follows in both directions
        Follow.objects.filter(
            Q(follower_id=user_id, following_id=target_user_id)
            | Q(follower_id=target_user_id, following_id=user_id)
        ).delete()

        return Block.objects.create(blocker_id=user_id, blocked_id=target_user_id)

    @staticmethod
    def unblock_user(user_id: int, target_user_id: int) -> None:
        BlockService._get_user_or_raise(target_user_id)

        deleted, _ = Block.objects.filter(
            blocker_id=user_id, blocked_id=target_user_id
        ).delete()
        if not deleted:
            raise MUError(MUErrorCode.NOT_BLOCKED)

    @staticmethod
    def is_blocked(user_id: int, other_id: int) -> bool:
        return Block.objects.filter(
            Q(blocker_id=user_id, blocked_id=other_id)
            | Q(blocker_id=other_id, blocked_id=user_id)
        ).exists()


class PostService:
    @staticmethod
    def get_post(post_id: int, viewer_id: int | None = None) -> Post:
        try:
            return _annotate_posts(
                Post.objects.select_related("author"), viewer_id
            ).get(pk=post_id)
        except Post.DoesNotExist:
            raise MUError(MUErrorCode.POST_DOES_NOT_EXIST)

    @staticmethod
    def get_like_count(post_id: int) -> int:
        return PostLike.objects.filter(post_id=post_id).count()

    @staticmethod
    def is_liked_by(post_id: int, user_id: int) -> bool:
        return PostLike.objects.filter(post_id=post_id, user_id=user_id).exists()

    @staticmethod
    def get_user_posts(
        user_id: int, start: int, end: int, viewer_id: int | None = None
    ) -> QuerySet[Post]:
        return _annotate_posts(
            Post.objects.filter(author_id=user_id)
            .select_related("author")
            .order_by("-time_posted"),
            viewer_id,
        )[start:end]

    @staticmethod
    def create_post(user_id: int, content: str, event_id: int | None = None) -> Post:
        validate_post(content)

        if event_id is not None:
            from main.event.services import EventService

            EventService.get_event(event_id, user_id, MemberRole.MODERATOR)

        return Post.objects.create(content=content, author_id=user_id, event_id=event_id)

    @staticmethod
    def like_post(user_id: int, post_id: int) -> None:
        try:
            post = Post.objects.get(pk=post_id)
        except Post.DoesNotExist:
            raise MUError(MUErrorCode.POST_DOES_NOT_EXIST)
        post.liked_by.add(user_id)

    @staticmethod
    def unlike_post(user_id: int, post_id: int) -> None:
        try:
            post = Post.objects.get(pk=post_id)
        except Post.DoesNotExist:
            raise MUError(MUErrorCode.POST_DOES_NOT_EXIST)
        post.liked_by.remove(user_id)


class CommentService:
    @staticmethod
    def has_replies(comment_id: int) -> bool:
        return Comment.objects.filter(parent_id=comment_id).exists()

    @staticmethod
    def get_like_count(comment_id: int) -> int:
        return CommentLike.objects.filter(comment_id=comment_id).count()

    @staticmethod
    def is_liked_by(comment_id: int, user_id: int) -> bool:
        return CommentLike.objects.filter(
            comment_id=comment_id, user_id=user_id
        ).exists()

    @staticmethod
    def comment_on_post(user_id: int, post_id: int, text: str) -> Comment:
        validate_comment_length(text, MUErrorCode.COMMENT_MAX_LENGTH)
        try:
            Post.objects.get(pk=post_id)
        except Post.DoesNotExist:
            raise MUError(MUErrorCode.POST_DOES_NOT_EXIST)
        return Comment.objects.create(user_id=user_id, post_id=post_id, text=text)

    @staticmethod
    def comment_on_event(user_id: int, event_id: int, text: str) -> Comment:
        validate_comment_length(text, MUErrorCode.COMMENT_MAX_LENGTH)
        try:
            Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            raise MUError(MUErrorCode.EVENT_DOES_NOT_EXIST)
        return Comment.objects.create(user_id=user_id, event_id=event_id, text=text)

    @staticmethod
    def reply_to_comment(user_id: int, comment_id: int, text: str) -> Comment:
        validate_comment_length(text, MUErrorCode.COMMENT_MAX_LENGTH)
        try:
            parent = Comment.objects.get(pk=comment_id)
        except Comment.DoesNotExist:
            raise MUError(MUErrorCode.COMMENT_DOES_NOT_EXIST)

        validate_comment_nesting(parent)

        return Comment.objects.create(
            user_id=user_id,
            text=text,
            parent=parent,
            post_id=parent.post_id,
            event_id=parent.event_id,
        )

    @staticmethod
    def like_comment(user_id: int, comment_id: int) -> None:
        if not Comment.objects.filter(pk=comment_id).exists():
            raise MUError(MUErrorCode.COMMENT_DOES_NOT_EXIST)
        CommentLike.objects.get_or_create(comment_id=comment_id, user_id=user_id)

    @staticmethod
    def unlike_comment(user_id: int, comment_id: int) -> None:
        try:
            Comment.objects.get(pk=comment_id)
        except Comment.DoesNotExist:
            raise MUError(MUErrorCode.COMMENT_DOES_NOT_EXIST)
        CommentLike.objects.filter(comment_id=comment_id, user_id=user_id).delete()

    @staticmethod
    def get_comments_for_post(
        post_id: int, start: int, end: int, viewer_id: int | None = None
    ) -> QuerySet[Comment]:
        return _annotate_comments(
            Comment.objects.filter(post_id=post_id, parent__isnull=True).order_by(
                "-time_posted"
            ),
            viewer_id,
        )[start:end]

    @staticmethod
    def get_comments_for_event(
        event_id: int, start: int, end: int, viewer_id: int | None = None
    ) -> QuerySet[Comment]:
        return _annotate_comments(
            Comment.objects.filter(event_id=event_id, parent__isnull=True).order_by(
                "-time_posted"
            ),
            viewer_id,
        )[start:end]
