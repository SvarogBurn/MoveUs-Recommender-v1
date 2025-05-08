import asyncio
import enum

## IMPORTANT!! This method only works while the backend is running on a single instance, when scaling horizontally becomes neccessary, a different approach will have to be used.

chat_events: dict[str, asyncio.Event] = {}

class ChatEventType(enum.IntEnum):
    MessageEvent = 0
    LastOpenEvent = 1

key_format = lambda type, id : f"${type}:{id}"

def get_chat_event(type: ChatEventType, id: int):
    key = key_format(type, id)
    if key not in chat_events:
        chat_events[key] = asyncio.Event()
    return chat_events[key]

async def wait_for_chat_event(type: ChatEventType, id: int):
    event = get_chat_event(type, id)
    await event.wait()
    event.clear()

def notifiy_chat_event(type: ChatEventType, id: int):
    event = get_chat_event(type, id)
    event.set()

