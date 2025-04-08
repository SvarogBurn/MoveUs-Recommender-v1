from main_app.graphql.error import MUError, MUErrorCode
from main_app.models.enums import CountryCode
from ..models import Location

def get_or_create_location(
        location_id: int = None,
        location_longitude: float = None,
        location_latitude: float = None,
        location_address_line1: str = None,
        location_address_line2: str = None,
        location_zip_code: int = None,
        location_region: str = None,
        location_name: str = None,
        location_country_code: CountryCode = None
    ):

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

        return location