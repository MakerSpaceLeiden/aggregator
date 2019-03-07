## Chores feature

A "chore" is a one-shot or recurring (configurable in different ways) event that requires a certain 
number of members to be carried out.

The aggregator is where the logic lives, and the CRM only provides a way to create the DB records, 
show the upcoming chores and allow volunteering.

### State

The "Chores" table contains the chores. The actual events are not stored in the DB, but computed 
on the fly by the aggregator. A given event is uniquely identified by the chore "name" and the 
timestamp. The "Chore volunteers" table contains the volunteering sign ups, and contains the above 
pair identifying the chore event + the user. In this regard, the DB schema is not properly normalized, 
so, in case a chore was changed (like periodicity or starting day), it might be that some volunteering 
signups would remain "orphan". But that's ok, as it simplifies the management of "events", that 
don't need to be stored in the DB, updated, and so forth.

### Lifecycle

Each chore can have multiple "reminders" (configured via JSON). A reminder is a way to help users
engage and follow up on the given chore, either by signing up for volunteering, or being reminded
of the chore itself, to which they have signed up. The reminder type "missing_volunteers" is meant
to gather volunteers, by asking on the mailing list, or via the BOT. The type "volunteers_who_signed_up"
is meant to remind those who signed up to honour the committment.

Each reminder can have multiple "nudges" (configured via JSON). A nudge has a unique key, so that the 
system can remember (via Redis) whether the nudge was excercised, and can be of different types. 

An "email" nudge is performed by sending an email.

A "volunteer_via_chat_bot" nudge is performed by sending messages via Telegram or Signal, to the
relevant users.

### Algorithm

The aggregator periodically executes the function "send_warnings_for_chores", which computes nudges to
send out by considering a time window configured in the main entry points (a couple of hours or so).
By looking into every chore, it finds the one that has reminders set for the most number of days in 
the past. It then calculates every event for that many days in the future, so that every potentially
relevant reminder is taken into consideration, and filters those that actually have reminders falling
into the given time window. For each event it finally calculates what reminders have set off (i.e. fall
into the past). By looking into Redis it sends out those nudges that haven't been processed yet.

The 2 main ideas behind this algorithm are:

1. The future lookup: considering that for every chore there is a potentially infinite sequence of events, 
looking up for a number of days equal to the earliest of the reminders is a way to
effectively limit the search to the only events that could generate a relevant reminder.

2. The time window: because the system is asynchronous, we don't send out nudges at the exact moment
when it should happen, but we only find out later (when the "send_warnings_for_chores" is executed) that
a given nudge has transitioned to the past. So, in order to not send nudges twice, we store the nudge
key inside Redis for those that have been processed already. But the number of these keys would grow 
indefinitely as time passes. Hence the time window idea: we only look as far back in the past as the
time window (a couple of hours), and we let the Redis keys expire after some time (twice the time window).
This way we effectively limit the usage of Redis and contain the complexity of the search algorithm. The
trade-off is that the system should never be down for a longer period than the configured time window.
