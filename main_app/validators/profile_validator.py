from .validation_error import ValidationError
import datetime

def profile_validator(
        first_name: str = None,
        last_name: str = None,
        date_of_birth: datetime.date = None,
        bio: str = None
        ):
    
    if first_name is not None:
        if not first_name: raise ValidationError("First name cannot be empty.")
        if len(first_name) > 32:
            raise ValidationError("First name cannot be longer than 32 characters.")

    if last_name is not None:
        if not last_name: raise ValidationError("Last name cannot be empty.")
        if len(last_name) > 32:
            raise ValidationError("Last name cannot be longer than 32 characters.")

    if date_of_birth:
        age = (datetime.date.today() - date_of_birth).days / 365
        if age < 18 : raise ValidationError("Must be over 18.")
        if age > 100 : raise ValidationError("Surely not that old.")

    if bio and len(bio) > 512:
        raise ValidationError("Bio length cannot longer than 512 characters.")