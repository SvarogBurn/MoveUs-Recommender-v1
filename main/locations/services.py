from typing import Any

from main.locations.models import Location


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
                from shared.errors.mu_error import MUError, MUErrorCode

                raise MUError(MUErrorCode.LOCATION_DOES_NOT_EXIST)
        return Location.objects.create(longitude=longitude, latitude=latitude, **kwargs)

    @staticmethod
    def release(location: Location) -> None:
        location.consider_dying()
