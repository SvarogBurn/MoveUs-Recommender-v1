import json

import graphene
from django.db.models import Q

from main_app.graphql.social.types import RelationshipType
from main_app.models.event import EventMemberLike

from ...models import Relationship, User, UserPrivacySetting
from ...models.enums import (
    FormedRelationshipsType,
    Gender,
    PreferredPartnerCharacteristics,
    PrivacyScope,
    PrivacySetting,
    RelationshipStatus,
)
from ..location.types import LocationType
from ..object_type import MUObjectType


class UserTypeMixin():
    likes = graphene.Int()
    dislikes = graphene.Int()

    def resolve_likes(self: User, info):
        return EventMemberLike.objects.filter(
            user_2 = self,
            like = True
        ).count()
    
    def resolve_dislikes(self: User, info):
        return EventMemberLike.objects.filter(
            user_2 = self,
            like = False
        ).count()

class ProfileType(MUObjectType, UserTypeMixin):
    class Meta:
        model = User
        exclude = (
            'is_superuser', 'is_staff', 'post_set', 'postcomment_set', 'friends_added', 'friends_added_by'
        )

    def resolve_formed_relationship_types(self: User, info):
        frt_formatted = [
            next(n for n, v in vars(FormedRelationshipsType).items() if v == x)
            for x in self.formed_relationship_types
        ]
        return frt_formatted
    
    def resolve_preferred_partner_characteristics(self: User, info):
        frt_formatted = [
            next(n for n, v in vars(PreferredPartnerCharacteristics).items() if v == x)
            for x in self.formed_relationship_types
        ]
        return frt_formatted

class UserType(MUObjectType, UserTypeMixin):
    location = graphene.Field(LocationType)
    email = graphene.String()
    date_of_birth = graphene.Date()
    gender = Gender.as_graphene_enum()
    friends = graphene.List(lambda: UserType)
    friend_count = graphene.Int()
    relationship = graphene.Field(RelationshipType)

    class Meta:
        model = User
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
            "preferred_activities"
        )

    def resolve_friend_count(self: User, info):
        user1_q = Q(user_1 = self)
        user2_q = Q(user_2 = self)

        return Relationship.objects.filter(user1_q | user2_q, status = RelationshipStatus.FRIENDS).count()
    
    def resolve_location(self: User, info):
        if self.id == info.context.user.id: return self.location
        ups = UserPrivacySetting.objects.get(user=self, setting=PrivacySetting.LOCATION)
        if ups.scope == PrivacyScope.EVERYONE:
            return self.location
        if ups.scope == PrivacyScope.FRIENDS and info.context.user.id:
            q1 = Q(user_1 = self, user_2 = info.context.user)
            q2 = Q(user_2 = self, user_1 = info.context.user)
            rel = Relationship.objects.filter(q1 | q2, status = RelationshipStatus.FRIENDS)
            if len(rel): return self.location

    def resolve_email(self: User, info):
        if self.id == info.context.user.id: return self.email
        ups = UserPrivacySetting.objects.get(user=self, setting=PrivacySetting.EMAIL)
        if ups.scope == PrivacyScope.EVERYONE:
            return self.email
        if ups.scope == PrivacyScope.FRIENDS and info.context.user.id:
            q1 = Q(user_1 = self, user_2 = info.context.user)
            q2 = Q(user_2 = self, user_1 = info.context.user)
            rel = Relationship.objects.filter(q1 | q2, status = RelationshipStatus.FRIENDS)
            if len(rel): return self.email

    def resolve_date_of_birth(self: User, info):
        if self.id == info.context.user.id: return self.date_of_birth
        ups = UserPrivacySetting.objects.get(user=self, setting=PrivacySetting.AGE)
        if ups.scope == PrivacyScope.EVERYONE:
            return self.date_of_birth
        if ups.scope == PrivacyScope.FRIENDS and info.context.user.id:
            q1 = Q(user_1 = self, user_2 = info.context.user)
            q2 = Q(user_2 = self, user_1 = info.context.user)
            rel = Relationship.objects.filter(q1 | q2, status = RelationshipStatus.FRIENDS)
            if len(rel): return self.date_of_birth

    def resolve_gender(self: User, info):
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

    def resolve_relationship(self: User, info):

        if info.context.user is None: return None
        q1 = Q(user_1 = self, user_2 = info.context.user)
        q2 = Q(user_2 = self, user_1 = info.context.user)
        rels = Relationship.objects.filter(q1 | q2)
        return rels[0] if len(rels) else None


class PrivacySettingType(MUObjectType):

    class Meta:
        model = UserPrivacySetting
        fields = (
            "setting",
            "scope"
        )
        convert_choices_to_enum = False