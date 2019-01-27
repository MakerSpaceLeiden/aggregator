import asyncio


class HttpServerInputMessageQueue(object):
    def __init__(self, asyncio_loop):
        self.msg_queue = asyncio.Queue()
        self.asyncio_loop = asyncio_loop

    def send_message(self, **kwargs):
        """
        Send a message to the asyncio-based http server from an external thread.
        """
        coro = self.msg_queue.put(kwargs)
        asyncio.run_coroutine_threadsafe(coro, self.asyncio_loop)

    async def get_next_message(self):
        """
        Fetch the next message from the queue. Wait until a message is available.
        To be called only from the main asyncio-based thread.
        """
        return await self.msg_queue.get()

