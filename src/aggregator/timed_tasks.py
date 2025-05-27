import asyncio

import aiocron


def start_checking_for_stale_checkins(aggregator, worker_input_queue, crontab, logger):
    @aiocron.crontab(crontab)
    @asyncio.coroutine
    def early_in_the_morning():
        worker_input_queue.add_task(aggregator.clean_stale_user_checkins, logger)


def start_checking_for_chores(aggregator, worker_input_queue, logger):
    @aiocron.crontab("*/5 * * * *")  # Every five minutes
    @asyncio.coroutine
    def early_in_the_morning():
        worker_input_queue.add_task(aggregator.send_warnings_for_chores, logger)


def start_checking_for_off_machines(aggregator, worker_input_queue, logger):
    @aiocron.crontab("*/5 * * * *")  # Every five minutes
    @asyncio.coroutine
    def early_in_the_morning():
        worker_input_queue.add_task(aggregator.check_expired_machine_state, logger)


class TaskScheduler(object):
    def __init__(self, clock, logger):
        self.logger = logger.getLogger(subsystem="task_scheduler")
        self.clock = clock
        self.scheduled_tasks = []

    def schedule_task_at_time(self, time, function, logger):
        self.scheduled_tasks.append((time, function, logger))

    def start_running_scheduled_tasks(self, worker_input_queue):
        @aiocron.crontab("* * * * *")  # Every minute
        @asyncio.coroutine
        def execute_for_due_tasks():
            worker_input_queue.add_task(self.actually_execute_due_tasks, self.logger)

    def actually_execute_due_tasks(self, _logger):
        for function, logger in self._extract_due_tasks():
            function(logger)

    def _extract_due_tasks(self):
        now = self.clock.now()
        tasks_left = []
        tasks_due = []
        for time, function, logger in self.scheduled_tasks:
            if time < now:
                tasks_due.append((function, logger))
            else:
                tasks_left.append((time, function, logger))
        self.scheduled_tasks = tasks_left
        return tasks_due
