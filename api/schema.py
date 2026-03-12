from graphene import Schema

from api.graphql import mutation, query, subscription
from api.graphql.unreferenced_types import unreferenced_types

schema = Schema(
    query=query.Queries,
    mutation=mutation.Mutations,
    subscription=subscription.Subscriptions,
    types=unreferenced_types,
)
