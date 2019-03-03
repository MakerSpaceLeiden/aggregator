class ChoreEvent(object):
    def __init__(self, chore, ts):
        self.chore = chore
        self.ts = ts

    def for_json(self):
        return {
            'chore': self.chore.for_json(),
            'when': {
                'timestamp': self.ts.as_int_timestamp(),
                'human_str': self.ts.human_str(),
            }
        }
