import graphene

from main.event.services import EventService
from main.location.services import LocationService
from main.user.models import User
from shared.enums import CountryCode, MemberRole
from shared.utils.decorators import require_auth


# TODO: Change mutations to NOT return boolean
class AlterProfileLocation(graphene.Mutation):

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

        LocationService.alter_profile_location(user, longitude, latitude)

        return AlterProfileLocation(success=True)


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

        LocationService.alter_event_location(
            event,
            location_longitude=location_longitude,
            location_latitude=location_latitude,
            location_address_line1=location_address_line1,
            location_address_line2=location_address_line2,
            location_zip_code=location_zip_code,
            location_country_code=location_country_code,
            location_region=location_region,
            location_name=location_name,
        )

        return AlterEventLocation(success=True)


class Mutation(graphene.ObjectType):
    alter_profile_location = AlterProfileLocation.Field()
    alter_event_location = AlterEventLocation.Field()
