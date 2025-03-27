from graphene import Schema

from .graphql import query, mutation

schema = Schema(query=query.Queries)