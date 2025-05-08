from inspect import getmembers, isclass
import os, graphene, importlib

class SubscriptionsAbstract(graphene.ObjectType):
    pass

subscriptions_base_classes = [SubscriptionsAbstract]
current_directory = os.path.dirname(os.path.abspath(__file__))
subdirectories = [
    x
    for x in os.listdir(current_directory)
    if os.path.isdir(os.path.join(current_directory, x)) and
    x != '__pycache__'
]

for directory in subdirectories:
    try:
        module = importlib.import_module(f'main_app.graphql.{directory}.subscriptions')
        if module:
            classes = [x for x in getmembers(module, isclass)]
            subscriptions = [x[1] for x in classes if 'Subscription' in x[0]]
            subscriptions_base_classes += subscriptions
    except ModuleNotFoundError:
        pass

subscriptions_base_classes = subscriptions_base_classes[::-1]
properties = {}
for base_class in subscriptions_base_classes:
    properties.update(base_class.__dict__['_meta'].fields)

Subscriptions = type(
    'Subscriptions',
    tuple(subscriptions_base_classes),
    properties
)