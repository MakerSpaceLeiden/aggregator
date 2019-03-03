from .chore_types.empty_trash import EmptyTrash


ALL_CHORE_TYPES = [
    EmptyTrash,
]


def get_chore_type_class(chore):
    for chore_class in ALL_CHORE_TYPES:
        if chore_class.__name__ == chore.class_type:
            return chore_class
    raise Exception(f'Cannot find Python class for chore of type "{chore.class_type}"')


def build_chore_instance(chore):
    chore_class = get_chore_type_class(chore)
    return chore_class(chore.chore_id, chore.name, chore.description, **chore.configuration)


class ChoresLogic(object):
    def __init__(self, chores):
        self.chores = [build_chore_instance(chore) for chore in chores]

    def get_events_from_to(self, ts_from, ts_to):
        events = []
        for chore in self.chores:
            events.extend(chore.iter_events_from_to(ts_from, ts_to))
        events.sort(key = lambda c: c.ts)
        return events
