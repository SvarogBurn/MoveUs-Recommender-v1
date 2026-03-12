import graphene

from api.graphql.object_type import MUObjectType
from main.social.models import Post, PostComment, Relationship
from main.user.models import User
from shared.enums import RelationshipStatus as RS
from shared.storage import storage_backend


class PostCommentType(MUObjectType):
    has_replies = graphene.Boolean()

    class Meta:
        model = PostComment
        include = ("id", "user", "text", "time_posted", "replies")

    def resolve_has_replies(self: PostComment, info: graphene.ResolveInfo) -> bool:
        return self.replies.count() != 0


class PostTypeMixin(MUObjectType):
    likes = graphene.Int()
    comments = graphene.List(
        PostCommentType,
        start=graphene.Int(default_value=0),
        end=graphene.Int(default_value=10),
    )

    class Meta:
        model = Post

    def resolve_likes(self: Post, info: graphene.ResolveInfo, **kwargs) -> int:
        return self.liked_by.count()

    def resolve_comments(
        self: Post, info: graphene.ResolveInfo, start: int, end: int, **kwargs
    ):
        return (
            PostComment.objects.order_by("time_posted")
            .reverse()
            .filter(post=self, is_reply_to__isnull=True)[start:end]
        )


class CreatePostType(PostTypeMixin):
    image_upload_URL = graphene.String()

    class Meta:
        model = Post

    def resolve_image_upload_URL(self: Post, info: graphene.ResolveInfo) -> str:
        return storage_backend.generate_post_picture_url(self.id)


class PostType(PostTypeMixin):

    class Meta:
        model = Post

class RelationshipType(MUObjectType):

    user = graphene.Field(graphene.lazy_import("api.graphql.user.types.UserType"))
    status = RS.as_graphene_enum()()

    class Meta:
        model = Relationship
        fields = ("last_update", "status", "chat")
        convert_choices_to_enum = False

    def resolve_status(
        self: Relationship, info: graphene.ResolveInfo
    ) -> str | None:
        if info.context.user is None:
            return None
        status = RS(self.status).name
        if self.status == RS.PENDING:
            status = (
                RS(RS.REQUEST_SENT).name
                if self.user_1 == info.context.user
                else RS(RS.REQUEST_RECEIVED).name
            )
        return status

    def resolve_user(
        self: Relationship, info: graphene.ResolveInfo
    ) -> User | None:
        if info.context.user is None:
            return None
        other = self.user_1 if self.user_2 == info.context.user else self.user_2
        return other
