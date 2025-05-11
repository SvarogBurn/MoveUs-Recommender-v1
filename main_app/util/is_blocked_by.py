from django.db.models import Q

from main_app.models import Relationship
from main_app.models.enums import RelationshipStatus


def is_blocked_by(user_id, by_id) -> bool:
    both = Q(status = RelationshipStatus.BLOCKED_BY_BOTH)
    single = Q(user_2_id = by_id, user_1_id = user_id, status = RelationshipStatus.BLOCKED_BY_ONE)

    return Relationship.objects.filter(
        both | single
    ).count() == 1
