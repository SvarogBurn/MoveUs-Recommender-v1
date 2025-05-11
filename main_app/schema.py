from graphene import Schema

from main_app.graphql import mutation, query, subscription
from main_app.graphql.unreferenced_types import unreferenced_types

schema = Schema(query=query.Queries, 
                mutation=mutation.Mutations, 
                subscription=subscription.Subscriptions, 
                types=unreferenced_types)
