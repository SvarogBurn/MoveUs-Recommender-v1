import graphene


class AttachmentType(graphene.ObjectType):
    id = graphene.String()
    url = graphene.String()