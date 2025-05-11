import asyncio
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.sessions.models import Session
from graphql import parse, validate

from main_app.schema import schema


@database_sync_to_async
def get_session(token: str)-> Session:
    return Session.objects.get(session_key=token)

class GraphQLSubscriptionConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        token: bytes = next(value for key, value in self.scope.get('headers') if key == b'authorization')
        if not token:
            await self.close()

        token = token.decode()
        
        try:
            session = await get_session(token)
            session = session.get_decoded()
            user_id = session.get('_auth_user_id')
            if user_id:
                self.scope['user_id'] = user_id
        except Session.DoesNotExist:
            await self.close()
            return

        await self.accept()
        self.subscriptions = {}
        self.keep_alive_task = None

    async def disconnect(self, close_code):
        # Clean up any subscriptions
        if self.keep_alive_task:
            self.keep_alive_task.cancel()
        for sub_id in list(self.subscriptions.keys()):
            await self.cleanup_subscription(sub_id)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get("type")
            
            if message_type == "connection_init":
                await self.handle_connection_init(data)
            elif message_type in ("start", "subscribe"):
                await self.handle_start(data)
            elif message_type == "stop":
                await self.handle_stop(data)
            elif message_type == "connection_terminate":
                await self.close()
            else:
                await self.send_message("error", None, {"message": "Unknown message type"})
                
        except json.JSONDecodeError:
            await self.send_message("error", None, {"message": "Invalid JSON"})

    async def handle_connection_init(self, data):
        # Send connection acknowledgement
        await self.send_message("connection_ack")
        
        # Start keep alive (optional but recommended)
        self.keep_alive_task = asyncio.create_task(self.send_keep_alive())

    async def send_keep_alive(self):
        while True:
            await asyncio.sleep(15)  # Send every 15 seconds
            try:
                await self.send_message("ka")
            except:
                break

    async def handle_start(self, data):
        payload = data.get("payload")
        query = payload.get("query")
        variables = payload.get("variables", {})
        operation_name = payload.get("operationName")
        subscription_id = data.get("id")

        if not query or not subscription_id:
            await self.send_message("error", subscription_id, {"message": "Missing query or subscription ID"})
            return

        try:
            # Parse and validate the GraphQL query
            document = parse(query)
            validation_errors = validate(schema.graphql_schema, document)
            
            if validation_errors:
                await self.send_message(
                    "error",
                    subscription_id,
                    {"errors": [e.message for e in validation_errors]}
                )
                return

            result = await schema.subscribe(
                query=query,
                variable_values=variables,
                operation_name=operation_name,
                context_value=self.get_context(),
            )

            if hasattr(result, "__aiter__"):
                # It's an async iterator (subscription)
                self.subscriptions[subscription_id] = result
                asyncio.create_task(self.handle_subscription_results(subscription_id, result))
            else:
                # It's a regular query/mutation result
                await self.send_message(
                    "data",
                    subscription_id,
                    {"data": result.data}
                )
                await self.send_message("complete", subscription_id)

        except Exception as e:
            await self.send_message(
                "error",
                subscription_id,
                {"message": str(e)}
            )

    async def handle_subscription_results(self, subscription_id, result):
        try:
            async for item in result:
                if subscription_id in self.subscriptions:  # Check if still active
                    await self.send_message(
                        "data",
                        subscription_id,
                        {"data": item.data}
                    )
        except Exception as e:
            if subscription_id in self.subscriptions:
                await self.send_message(
                    "error",
                    subscription_id,
                    {"message": str(e)}
                )
        finally:
            if subscription_id in self.subscriptions:
                await self.cleanup_subscription(subscription_id)
                await self.send_message("complete", subscription_id)

    async def handle_stop(self, data):
        subscription_id = data.get("id")
        if subscription_id in self.subscriptions:
            await self.cleanup_subscription(subscription_id)

    async def cleanup_subscription(self, subscription_id):
        if subscription_id in self.subscriptions:
            subscription = self.subscriptions.pop(subscription_id)
            if hasattr(subscription, "close"):
                await subscription.close()

    async def send_message(self, message_type, id=None, payload=None):
        message = {"type": message_type}
        if id is not None:
            message["id"] = id
        if payload is not None:
            message["payload"] = payload
        await self.send(text_data=json.dumps(message))

    def get_context(self):
        return {
            "request": self.scope,
            "consumer": self,
            "channel": self.channel_name,
        }