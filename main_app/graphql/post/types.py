import graphene

from graphene_django import DjangoObjectType

from ...models import Post, PostComment

class PostCommentType(DjangoObjectType):

    class Meta:
        model = PostComment
        fields = "__all__"

class PostType(DjangoObjectType):
    likes = graphene.Int()
    comments = graphene.List(PostCommentType, start=graphene.Int(default_value=0), end=graphene.Int(default_value=10))

    class Meta:
        model = Post
        fields = "__all__"

    def resolve_likes(self: Post, info, **kwargs):
        return self.liked_by.count()
    
    def resolve_comments(self: Post, info, start, end, **kwargs):
        return PostComment.objects.order_by('time_posted').reverse().filter(post=self, is_reply_to__isnull = True)[start:end]
    
