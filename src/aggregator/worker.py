import threading


class Worker(object):
    def __init__(self, input_queue):
        self.input_queue = input_queue

    def start_working_in_background_thread(self):
        thread = threading.Thread(target=self._main)
        thread.daemon = True
        thread.start()

    def _main(self):
        while True:
            task, respond, logger = self.input_queue.get_next_task_blocking()
            result = error = None
            try:
                result = task(logger)
            except Exception as err:
                error = err
            if respond:
                respond(error, result)
