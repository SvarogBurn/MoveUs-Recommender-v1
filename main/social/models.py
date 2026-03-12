from django.db import models, transaction
from django.db.models.fields.composite import CompositePrimaryKey

from main.chat.models import Chat
from main.events.models import Event
from main.users.models import User
from shared.enums import RelationshipStatus


class Relationship(models.Model):
    pk = CompositePrimaryKey("user_1", "user_2")
    user_1 = models.ForeignKey(
        User, on_delete=models.CASCADE, null=False, related_name="friends_added"
    )
    user_2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=False,
        related_name="friends_added_by",
    )
    last_update = models.DateTimeField(auto_now_add=True)
    status = models.SmallIntegerField(
        choices=RelationshipStatus.choices(), db_index=True
    )
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, null=True)

    class Meta:
        db_table = "main_app_relationship"

    def swap_users(self) -> None:
        user_1, user_2 = self.user_1, self.user_2

        with transaction.atomic():
            Relationship.objects.filter(user_1=user_1, user_2=user_2).update(
                user_1=user_2, user_2=user_1
            )

    def is_blocked(self, user) -> bool:
        if self.status == RelationshipStatus.BLOCKED_BY_BOTH:
            return True
        return user == self.user_2 and self.status == RelationshipStatus.BLOCKED_BY_ONE


class PostLike(models.Model):
    post = models.ForeignKey("Post", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = "main_app_post_liked_by"


class Post(models.Model):
    title = models.CharField(max_length=128)
    content = models.CharField()
    time_posted = models.DateTimeField(auto_now_add=True, db_index=True)
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, null=True, related_name="posts"
    )
    liked_by = models.ManyToManyField(
        User, through="PostLike", through_fields=("post", "user")
    )

    class Meta:
        db_table = "main_app_post"


class PostComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="comments", null=False
    )
    text = models.CharField(max_length=512)
    time_posted = models.DateTimeField(auto_now_add=True)
    is_reply_to = models.ForeignKey(
        "PostComment", on_delete=models.CASCADE, related_name="replies", null=True
    )

    class Meta:
        db_table = "main_app_postcomment"

    def get_tree(self) -> None:
        self.descendents = list(self.replies.all())
        for child in self.descendents:
            child.get_tree()
