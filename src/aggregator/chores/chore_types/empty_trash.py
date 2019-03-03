from datetime import datetime
from ...clock import Time
from ..event import ChoreEvent


class EmptyTrash(object):
    def __init__(self, chore_id, name, description, min_required_people, first_tuesday):
        self.chore_id = chore_id
        self.name = name
        self.description = description
        self.min_required_people = min_required_people
        self.first_tuesday = Time.from_datetime(datetime.strptime(first_tuesday, '%d/%m/%Y %H:%M'))

    # Once every other week
    def iter_events_from_to(self, ts_from, ts_to):
        ts = self.first_tuesday
        while ts <= ts_to:
            if ts >= ts_from:
                yield ChoreEvent(self, ts)
            ts = ts.add(14, 'days')

    def for_json(self):
        return {
            'chore_id': self.chore_id,
            'name': self.name,
            'description': self.description,
            'min_required_people': self.min_required_people,
        }
