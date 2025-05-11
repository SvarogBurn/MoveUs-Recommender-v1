import graphene
from django.db.models.fields.composite import CompositePrimaryKey
from graphene_django.types import DjangoObjectType


class MUObjectType(DjangoObjectType):

    def __init_subclass__(self):
        try:
            if not isinstance(self.Meta.model._meta.pk, CompositePrimaryKey):
                raise AttributeError()
        except AttributeError:
            self.id = graphene.Int(source='pk')
            
        super().__init_subclass__()

    class Meta:
        abstract = True    

    @classmethod
    def __init_subclass_with_meta__(cls, model=None, **options):
        super().__init_subclass_with_meta__(model=model, **options)

        for field in model._meta.fields:
            if field.choices:
                if hasattr(cls, f"resolve_{field.name}"):
                    continue

                # Override the field with a custom resolver that returns the display label
                cls._meta.fields[field.name] = graphene.Field(
                    graphene.String,
                    resolver=cls.generate_choice_label_resolver(field.name)
                )

    @staticmethod
    def generate_choice_label_resolver(field_name):
        def resolver(instance, info):
            method_name = f"get_{field_name}_display"
            if hasattr(instance, method_name):
                return getattr(instance, method_name)()
            return getattr(instance, field_name)
        return resolver
