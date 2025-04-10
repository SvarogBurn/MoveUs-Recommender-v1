import graphene

from datetime import datetime

from main_app.graphql.event.types import EventType
from main_app.models.location import Location
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

class AlterEvent(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)
        title = graphene.String(required = False)
        description = graphene.String(required = False)
        start_time = graphene.DateTime(required = False)
        end_time = graphene.DateTime(required = False)
        requrements = graphene.String(required = False)

    event = graphene.Field(EventType)

    @classmethod
    def mutate(
        cls,
        root,
        info,
        event_id: str = None,
        title: str = None,
        description: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        requirements: object = None,
    ):
        
        user: User = info.context.user
        if not user.id: raise MUError(MUErrorCode.AUTHENTIFICATION_ERROR)

        event_validator(
            title, description, start_time, end_time
        )

        event = None

        try:
            event = Event.objects.get(pk = event_id)
        except Event.DoesNotExist:
            raise MUError(MUErrorCode.EVENT_DOES_NOT_EXIST)

        try:
            em = EventMember.objects.get(pk=(user.id, event.id))
            if em.role != MemberRole.ORGANIZER:
                raise MUError(MUErrorCode.NOT_ORGANIZER)
        except EventMember.DoesNotExist:
            raise MUError(MUErrorCode.NOT_ORGANIZER)
        
        if title is not None: event.title = title
        if description is not None: event.description = description
        if start_time is not None: event.start_time = start_time
        if end_time is not None: event.end_time = end_time
        if requirements is not None: event.requirements = requirements

        event.save()

        return AlterEvent(
            event = event
        )

class DeleteEvent(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate(
        cls,
        root,
        info,
        event_id: str = None,
    ):
        
        user: User = info.context.user
        if not user.id: raise MUError(MUErrorCode.AUTHENTIFICATION_ERROR)

        event = None

        try:
            event = Event.objects.get(pk = event_id)
        except Event.DoesNotExist:
            raise MUError(MUErrorCode.EVENT_DOES_NOT_EXIST)

        try:
            em = EventMember.objects.get(pk=(user.id, event.id))
            if em.role != MemberRole.ORGANIZER:
                raise MUError(MUErrorCode.NOT_ORGANIZER)
        except EventMember.DoesNotExist:
            raise MUError(MUErrorCode.NOT_ORGANIZER)

        event.delete()

        return DeleteEvent(
            success = True
        )

class Mutation(graphene.ObjectType):
    add_event = AddEvent.Field()
    alter_event = AlterEvent.Field()
    delete_event = DeleteEvent.Field()
