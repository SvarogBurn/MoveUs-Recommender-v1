from datetime import datetime

import graphene

from main_app.graphql.event.types import EventType
from main_app.models.location import Location
from main_app.util import get_event, require_auth
from main_app.validators import event_validator, location_validator

from ...models import Event, EventMember, User
from ...models.enums import Activity, CountryCode, MemberRole, SkillLevel, GenderNoPNTS
from ..error import MUError, MUErrorCode


class CreateEventMutation(graphene.Mutation):

    class Arguments:
        title = graphene.String(required = True)
        description = graphene.String(required = False)
        start_time = graphene.DateTime(required = True)
        end_time = graphene.DateTime(required = True)
        requirements = graphene.String(required = False)
        location_id = graphene.Int(required = False)
        location_longitude = graphene.Float(required = False)
        location_latitude = graphene.Float(required = False)
        location_address_line1 = graphene.String(required = False)
        location_address_line2 = graphene.String(required = False)
        location_zip_code = graphene.Int(required = False)
        location_country_code = CountryCode.as_graphene_enum()(required = False)
        location_region = graphene.String(required = False)
        location_name = graphene.String(required = False)
        activity = Activity.as_graphene_enum()(required = True)
        skill_level = SkillLevel.as_graphene_enum()(required = True)
        max_participants = graphene.Int(required = False)
        allow_spectators = graphene.Boolean(required = False)
        min_age = graphene.Int(required=False)
        max_age = graphene.Int(required=False)
        accepted_genders = graphene.List(
            GenderNoPNTS.as_graphene_enum(),
            required=False
            )

    event = graphene.Field(EventType)

    @require_auth
    def mutate(
        self,
        info,
        title: str = None,
        description: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        requirements: object = None,
        location_id: int = None,
        location_longitude: float = None,
        location_latitude: float = None,
        location_address_line1: str = None,
        location_address_line2: str = None,
        location_zip_code: int = None,
        location_country_code: CountryCode = None,
        location_region: str = None,
        location_name: str = None,
        activity: Activity = None,
        skill_level: SkillLevel = None,
        max_participants: int = None,
        allow_spectators: bool = None,
        min_age: int = None,
        max_age: int = None,
        accepted_genders: list = None
    ):
        
        user: User = info.context.user

        if not location_id and not (location_longitude and location_latitude):
            raise MUError(MUErrorCode.MINIMAL_LOCATION_REQUIREMENTS_MISSING)

        location_validator(
            location_longitude, location_latitude,
            location_address_line1, location_address_line2,
            location_zip_code, location_region, location_name
        )

        event_validator(
            title, description, start_time, end_time, max_participants,
            min_age, max_age, accepted_genders
        )

        location = None

        if location_id:
            try:
                location = Location.objects.get(pk = location_id)
            except Location.DoesNotExist:
                raise MUError(MUErrorCode.LOCATION_DOES_NOT_EXIST)
        else:
            location = Location.objects.create(
                longitude = location_longitude,
                latitude = location_latitude,
                address_line_1 = location_address_line1,
                address_line_2 = location_address_line2,
                zip_code = location_zip_code,
                country_code = location_country_code,
                region = location_region,
                name = location_name 
            )
            
            location.save()

        event = Event.objects.create(
                title = title,
                description = description,
                start_time = start_time,
                end_time = end_time,
                location = location,
                requirements = requirements,
                activity_id = activity,
                skill_level = skill_level,
                max_participants = max_participants,
                allow_spectators = allow_spectators
            )
        
        EventMember.objects.create(
            event = event,
            user = info.context.user,
            role = MemberRole.ORGANIZER,
            has_participated = True
        )

        return CreateEventMutation(
            event = event
        )

class AlterEventMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)
        title = graphene.String(required = False)
        description = graphene.String(required = False)
        start_time = graphene.DateTime(required = False)
        end_time = graphene.DateTime(required = False)
        requrements = graphene.String(required = False)
        max_participants = graphene.Int(required = False)

    success = graphene.Boolean()

    @require_auth
    def mutate(
        self,
        info,
        event_id: str = None,
        title: str = None,
        description: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        requirements: object = None,
        max_participants: int = None,
    ):
        
        user: User = info.context.user

        event_validator(
            title, description, start_time, end_time, max_participants
        )

        event = get_event(event_id, user.id, MemberRole.ORGANIZER)

        if max_participants < event.participant_count():
            raise MUError(MUErrorCode.EVENT_MIN_MAX_PARTICIPANTS)
        
        if title is not None: event.title = title
        if description is not None: event.description = description
        if start_time is not None: event.start_time = start_time
        if end_time is not None: event.end_time = end_time
        if requirements is not None: event.requirements = requirements
        if max_participants is not None: event.max_participants = max_participants

        event.save()

        return AlterEventMutation(success = True)

class DeleteEventMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(
        self,
        info,
        event_id: str = None,
    ):
        
        user: User = info.context.user

        event = get_event(event_id, user.id, MemberRole.ORGANIZER)

        event.delete()

        return DeleteEventMutation(
            success = True
        )

class Mutation(graphene.ObjectType):
    create_event = CreateEventMutation.Field()
    alter_event = AlterEventMutation.Field()
    delete_event = DeleteEventMutation.Field()
