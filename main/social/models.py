from django.db import models
from django.db.models.fields.composite import CompositePrimaryKey

from main.event.models import Event
from main.user.models import User


class Follow(models.Model):
    pk = CompositePrimaryKey("follower", "following")
    follower = models.ForeignKey(
        User, on_delete=models.CASCADE, null=False, related_name="following_set"
    )
    following = models.ForeignKey(
        User, on_delete=models.CASCADE, null=False, related_name="followers_set"
    )
    time_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "main_app_follow"


class Block(models.Model):
    pk = CompositePrimaryKey("blocker", "blocked")
    blocker = models.ForeignKey(
        User, on_delete=models.CASCADE, null=False, related_name="blocking_set"
    )
    blocked = models.ForeignKey(
        User, on_delete=models.CASCADE, null=False, related_name="blocked_by_set"
    )
    time_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "main_app_block"


class Post(models.Model):
    content = models.CharField()
    time_posted = models.DateTimeField(auto_now_add=True, db_index=True)
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, null=False, related_name="authored_posts"
    )
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, null=True, related_name="posts"
    )
    liked_by = models.ManyToManyField(
        User, through="PostLike", through_fields=("post", "user")
    )

    class Meta:
        db_table = "main_app_post"


class PostLike(models.Model):
    pk = CompositePrimaryKey("post", "user")
    post = models.ForeignKey("Post", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = "main_app_post_liked_by"


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="comments", null=True
    )
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="social_comments", null=True
    )
    text = models.CharField(max_length=512)
    time_posted = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey(
        "Comment", on_delete=models.CASCADE, related_name="replies", null=True
    )

    class Meta:
        db_table = "main_app_comment"


class CommentLike(models.Model):
    pk = CompositePrimaryKey("comment", "user")
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = "main_app_comment_liked_by"
