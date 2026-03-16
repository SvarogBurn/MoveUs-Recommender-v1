from typing import Any

from main.location.models import Location
from main.location.validators import validate_location
from shared.errors.mu_error import MUError, MUErrorCode


class LocationService:
    @staticmethod
    def get_or_create(
        location_id: int | None = None,
        longitude: float | None = None,
        latitude: float | None = None,
        **kwargs: Any,
    ) -> Location:
        if location_id:
            try:
                return Location.objects.get(pk=location_id)
            except Location.DoesNotExist:
                raise MUError(MUErrorCode.LOCATION_DOES_NOT_EXIST)
        return Location.objects.create(longitude=longitude, latitude=latitude, **kwargs)

    @staticmethod
    def reference_count(location: Location) -> int:
        from main.event.models import Event

        return Event.objects.filter(location=location).count()

    @staticmethod
    def consider_dying(location: Location) -> None:
        if LocationService.reference_count(location) <= 1:
            location.delete()

    @staticmethod
    def release(location: Location) -> None:
        LocationService.consider_dying(location)

    @staticmethod
    def alter_event_location(
        event,
        location_longitude: float = None,
        location_latitude: float = None,
        location_address_line1: str = None,
        location_address_line2: str = None,
        location_zip_code: int = None,
        location_country_code=None,
        location_region: str = None,
        location_name: str = None,
    ) -> None:
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

        if LocationService.reference_count(location) > 1:
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

    @staticmethod
    def set_event_location(event, location_id: int) -> None:
        try:
            new_location = Location.objects.get(pk=location_id)
            old_location = event.location
            event.location = new_location
            event.save()
            LocationService.consider_dying(old_location)
        except Location.DoesNotExist:
            raise MUError(MUErrorCode.LOCATION_DOES_NOT_EXIST)

    @staticmethod
    def alter_profile_location(
        user, longitude: float, latitude: float
    ) -> None:
        validate_location(location_longitude=longitude, location_latitude=latitude)
        user.latitude = latitude
        user.longitude = longitude
        user.save()
