import graphene

from api.graphql.user.types import ProfileType
from main.events.models import Event, EventMember
from main.events.services import EventService
from main.locations.models import Location
from main.locations.validators import validate_location
from main.users.models import User
from shared.enums import CountryCode, MemberRole
from shared.errors.mu_error import MUError, MUErrorCode
from shared.utils.decorators import require_auth


# TODO: Change mutations to NOT return boolean
class UpdateProfileLocation(graphene.Mutation):

    class Arguments:
        longitude = graphene.Float()
        latitude = graphene.Float()

    success = graphene.Boolean()

    @require_auth
    def mutate(
        self,
        info: graphene.ResolveInfo,
        longitude: float = None,
        latitude: float = None,
    ):

        user: User = info.context.user

        validate_location(location_longitude=longitude, location_latitude=latitude)

        user.latitude = latitude
        user.longitude = longitude
        user.save()

        return UpdateProfileLocation(success=True)


class AlterEventLocation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int()
        location_longitude = graphene.Float(required=False)
        location_latitude = graphene.Float(required=False)
        location_address_line1 = graphene.String(required=False)
        location_address_line2 = graphene.String(required=False)
        location_zip_code = graphene.Int(required=False)
        location_country_code = CountryCode.as_graphene_enum()(required=False)
        location_region = graphene.String(required=False)
        location_name = graphene.String(required=False)

    success = graphene.Boolean()

    @require_auth
    def mutate(
        self,
        info: graphene.ResolveInfo,
        event_id: int = None,
        location_longitude: float = None,
        location_latitude: float = None,
        location_address_line1: str = None,
        location_address_line2: str = None,
        location_zip_code: int = None,
        location_country_code: CountryCode = None,
        location_region: str = None,
        location_name: str = None,
    ):

        user: User = info.context.user

        event = EventService.get_event(event_id, user.id, MemberRole.ORGANIZER)

        validate_location(
            location_longitude,
            location_latitude,
            location_address_line1,
            location_address_line2,
            location_zip_code,
            location_region,
            location_name,
        )

        location: Location = event.location

        if location.reference_count() > 1:
            location.pk = None

        if location_longitude:
            location.longitude = location_longitude
        if location_latitude:
            location.latitude = location_latitude
        if location_address_line1:
            location.address_line_1 = location_address_line1
        if location_address_line2:
            location.address_line_2 = location_address_line2
        if location_zip_code:
            location.zip_code = location_zip_code
        if location_country_code:
            location.country_code = location_country_code
        if location_region:
            location.region = (location_region,)
        if location_name:
            location.name = location_name
        location.save()

        return AlterEventLocation(success=True)


class SetEventLocation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int()
        location_id = graphene.Float(required=False)

    success = graphene.Boolean()

    @require_auth
    def mutate(
        self,
        info: graphene.ResolveInfo,
        event_id: int = None,
        location_id: int = None,
    ):

        user: User = info.context.user

        event = None

        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            raise MUError(MUErrorCode.EVENT_DOES_NOT_EXIST)

        try:
            em = EventMember.objects.get(pk=(user.id, event.id))
            if em.role != MemberRole.ORGANIZER:
                raise MUError(MUErrorCode.NOT_ORGANIZER)
        except EventMember.DoesNotExist:
            raise MUError(MUErrorCode.NOT_ORGANIZER)

        try:
            new_location = Location.objects.get(pk=location_id)
            old_location = event.location
            event.location = new_location
            event.save()
            old_location.consider_dying()
        except Location.DoesNotExist:
            raise MUError(MUErrorCode.LOCATION_DOES_NOT_EXIST)

        return SetEventLocation(success=True)


class Mutation(graphene.ObjectType):
    update_profile_location = UpdateProfileLocation.Field()
    alter_event_location = AlterEventLocation.Field()
    set_event_location = SetEventLocation.Field()
