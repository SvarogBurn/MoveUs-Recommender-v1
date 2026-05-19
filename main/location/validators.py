from shared.errors.mu_error import MUError, MUErrorCode


def validate_location(
    location_longitude: float = None,
    location_latitude: float = None,
    location_address_line1: str = None,
    location_address_line2: str = None,
    location_zip_code: int = None,
    location_region: str = None,
    location_name: str = None,
):

    if location_latitude and not -90 <= location_latitude <= 90:
        raise MUError(MUErrorCode.LATITUDE_VALUE)
    if location_longitude and not -180 <= location_longitude <= 180:
        raise MUError(MUErrorCode.LONGITUDE_VALUE)

    if location_name:
        if len(location_name) > 128:
            raise MUError(MUErrorCode.LOCATION_NAME_MAX_LENGTH)
        if len(location_name) < 4:
            raise MUError(MUErrorCode.LOCATION_NAME_MIN_LENGTH)
