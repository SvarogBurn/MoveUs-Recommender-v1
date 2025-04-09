import graphene

from datetime import datetime

from main_app.graphql.event.types import EventType
from main_app.util.get_or_create_location import get_or_create_location
from main_app.validators import location_validator, event_validator

from ..error import MUError, MUErrorCode
from ...models import User, Event, EventMember
from ...models.enums import SkillLevel, ActivityEnum, CountryCode, MemberRole

class AddEvent(graphene.Mutation):

    class Arguments:
        title = graphene.String(required = True)
        description = graphene.String(required = False)
        start_time = graphene.DateTime(required = True)
        end_time = graphene.DateTime(required = True)
        requrements = graphene.String(required = False)
        location_id = graphene.Int(required = False)
        location_longitude = graphene.Float(required = False)
        location_latitude = graphene.Float(required = False)
        location_address_line1 = graphene.String(required = False)
        location_address_line2 = graphene.String(required = False)
        location_zip_code = graphene.Int(required = False)
        location_country_code = CountryCode.as_graphene_enum()(required = False)
        location_region = graphene.String(required = False)
        location_name = graphene.String(required = False)
        activity = ActivityEnum.as_graphene_enum()(required = True)
        skill_level = SkillLevel.as_graphene_enum()(required = True)

    event = graphene.Field(EventType)

    @classmethod
    def mutate(
        cls,
        root,
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
        activity: ActivityEnum = None,
        skill_level: SkillLevel = None
    ):
        
        user: User = info.context.user
        if not user.id: raise MUError(MUErrorCode.AUTHENTIFICATION_ERROR)

        if not location_id and not (location_longitude and location_latitude):
            raise MUError(MUErrorCode.MINIMAL_LOCAION_REQUIREMENTS_MISSING)

        location_validator(
            location_longitude, location_latitude,
            location_address_line1, location_address_line2,
            location_zip_code, location_region, location_name
        )

        event_validator(
            title, description, start_time, end_time
        )

        location = get_or_create_location(
            location_id, location_longitude, location_latitude,
            location_address_line1, location_address_line2,
            location_zip_code, location_region, location_name,
            location_country_code
        )

        event = Event.objects.create(
                title = title,
                description = description,
                start_time = start_time,
                end_time = end_time,
                location = location,
                requirements = requirements,
                activity_id = activity,
                skill_level = skill_level
            )
        
        EventMember.objects.create(
            event = event,
            user = info.context.user,
            role = MemberRole.ORGANIZER
        )

        return AddEvent(
            event = event
        )        

class Mutation(graphene.ObjectType):
    add_event = AddEvent.Field()
