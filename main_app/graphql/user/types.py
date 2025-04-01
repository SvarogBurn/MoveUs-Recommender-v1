from graphene_django import DjangoObjectType
from django.db.models import Q

import graphene

from ...models import MoveusUser, UserPrivacySetting, Relationship
from ...models.enums import PrivacyScope, RelationshipStatus, Gender, PrivacySetting

from ..location.types import LocationType

class ProfileType(DjangoObjectType):
    class Meta:
        model = MoveusUser
        exclude = (
            'is_superuser', 'is_staff', 'post_set', 'postcomment_set', 'friends_added', 'friends_added_by'
        )

class UserType(DjangoObjectType):
    location = graphene.Field(LocationType)
    email = graphene.String()
    date_of_birth = graphene.Date()
    gender = Gender.as_graphene_enum()
    friends = graphene.List(lambda: UserType)
    friend_count = graphene.Int()

    class Meta:
        model = MoveusUser
        fields = (
            "id",
            "bio",
            "first_name",
            "last_name",
            "xp",
            "verified",
            "gender",
            "username",
            "is_active",
            "date_joined",
            "img_url"
        )

    def resolve_friend_count(self: MoveusUser, info):
        user1_q = Q(user_1 = self)
        user2_q = Q(user_2 = self)

        return Relationship.objects.filter(user1_q | user2_q, status = RelationshipStatus.FRIENDS).count()
    
    def resolve_location(self: MoveusUser, info):
        if self.id == info.context.user.id: return self.location
        ups = UserPrivacySetting.objects.get(user=self, setting=PrivacySetting.LOCATION)
        if ups.scope == PrivacyScope.EVERYONE:
            return self.location
        if ups.scope == PrivacyScope.FRIENDS and info.context.user.id:
            q1 = Q(user_1 = self, user_2 = info.context.user)
            q2 = Q(user_2 = self, user_1 = info.context.user)
            rel = Relationship.objects.filter(q1 | q2, status = RelationshipStatus.FRIENDS)
            if len(rel): return self.location

    def resolve_email(self: MoveusUser, info):
        if self.id == info.context.user.id: return self.email
        ups = UserPrivacySetting.objects.get(user=self, setting=PrivacySetting.EMAIL)
        if ups.scope == PrivacyScope.EVERYONE:
            return self.email
        if ups.scope == PrivacyScope.FRIENDS and info.context.user.id:
            q1 = Q(user_1 = self, user_2 = info.context.user)
            q2 = Q(user_2 = self, user_1 = info.context.user)
            rel = Relationship.objects.filter(q1 | q2, status = RelationshipStatus.FRIENDS)
            if len(rel): return self.email

    def resolve_date_of_birth(self: MoveusUser, info):
        if self.id == info.context.user.id: return self.date_of_birth
        ups = UserPrivacySetting.objects.get(user=self, setting=PrivacySetting.AGE)
        if ups.scope == PrivacyScope.EVERYONE:
            return self.date_of_birth
        if ups.scope == PrivacyScope.FRIENDS and info.context.user.id:
            q1 = Q(user_1 = self, user_2 = info.context.user)
            q2 = Q(user_2 = self, user_1 = info.context.user)
            rel = Relationship.objects.filter(q1 | q2, status = RelationshipStatus.FRIENDS)
            if len(rel): return self.date_of_birth

    def resolve_gender(self: MoveusUser, info):
        if self.id == info.context.user.id: return self.gender
        ups = UserPrivacySetting.objects.get(user=self, setting=PrivacySetting.GENDER)
        if ups.scope == PrivacyScope.EVERYONE:
            return self.gender
        if ups.scope == PrivacyScope.FRIENDS and info.context.user.id:
            q1 = Q(user_1 = self, user_2 = info.context.user)
            q2 = Q(user_2 = self, user_1 = info.context.user)
            rel = Relationship.objects.filter(q1 | q2, status = RelationshipStatus.FRIENDS)
            if len(rel): return self.gender

    def resolve_friends(self, info):

        def all_friends():
            user1_q = Q(user_1 = self)
            user2_q = Q(user_2 = self)

            rels = Relationship.objects.filter(user1_q | user2_q, status = RelationshipStatus.FRIENDS)
            return [
                r.user_1 if self.id == r.user_2.id else r.user_2 for r in rels
            ]
    
        if self.id == info.context.user.id: return all_friends()
        ups = UserPrivacySetting.objects.get(user=self, setting=PrivacySetting.FRIENDS)
        if ups.scope == PrivacyScope.EVERYONE:
            return all_friends()
        if ups.scope == PrivacyScope.FRIENDS and info.context.user.id:
            q1 = Q(user_1 = self, user_2 = info.context.user)
            q2 = Q(user_2 = self, user_1 = info.context.user)
            rel = Relationship.objects.filter(q1 | q2, status = RelationshipStatus.FRIENDS)
            if len(rel): return all_friends()


class PrivacySettingType(DjangoObjectType):

    class Meta:
        model = UserPrivacySetting
        fields = (
            "setting",
            "scope"
        )
        convert_choices_to_enum = False