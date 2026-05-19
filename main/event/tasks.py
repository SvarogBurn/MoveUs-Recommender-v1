from celery import shared_task

from main.event.models import Event
from main.notification.services import NotificationService
from shared.enums import EventPhase


@shared_task
def transition_event_to_in_progress(event_id: int) -> None:
    updated = Event.objects.filter(
        id=event_id, phase=EventPhase.SCHEDULED
    ).update(phase=EventPhase.IN_PROGRESS)
    if not updated:
        return
    NotificationService.send_event_started(event_id)


@shared_task
def transition_event_to_finished(event_id: int) -> None:
    updated = Event.objects.filter(
        id=event_id, phase=EventPhase.IN_PROGRESS
    ).update(phase=EventPhase.FINISHED)
    if not updated:
        return
    NotificationService.send_event_finished(event_id)
