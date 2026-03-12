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

    if location_address_line1 and len(location_address_line1) > 64:
        raise MUError(MUErrorCode.ADDRESS_LINE_MAX_LENGTH)

    if location_address_line2 and len(location_address_line2) > 64:
        raise MUError(MUErrorCode.ADDRESS_LINE_MAX_LENGTH)

    if location_zip_code and not 1e5 <= location_zip_code < 1e6:
        raise MUError(MUErrorCode.ZIP_CODE_VALUE)

    if location_region and len(location_region) > 32:
        raise MUError(MUErrorCode.REGION_MAX_LENGTH)

    if location_name:
        if len(location_name) > 32:
            raise MUError(MUErrorCode.LOCATION_NAME_MAX_LENGTH)
        if len(location_name) < 4:
            raise MUError(MUErrorCode.LOCATION_NAME_MIN_LENGTH)
