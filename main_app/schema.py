from graphene import Schema

from main_app.graphql import query, mutation, subscription

schema = Schema(query=query.Queries, mutation=mutation.Mutations, subscription=subscription.Subscriptions)
