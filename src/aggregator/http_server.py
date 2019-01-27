import asyncio
from aggregator.mqtt_client import MqttListenerClient
from aggregator.communication import HttpServerInputMessageQueue
from aggregator.database import MySQLAdapter
from aggregator.redis import RedisAdapter
from aggregator.logic import Aggregator
from aggregator.logging import Logger


logger = Logger(subsystem='root')


aggregator = Aggregator(
    MySQLAdapter(),
    RedisAdapter(),
)


loop = asyncio.get_event_loop()
q = HttpServerInputMessageQueue(loop)
mqtt_listener_client = MqttListenerClient(q)
mqtt_listener_client.start_listening_on_a_background_thread()


from quart import Quart, websocket

app = Quart('aggregator')


@app.route('/')
async def hello():
    return 'hello'


@app.route('/quit')
async def quit():
    mqtt_listener_client.loop_stop()
    return 'stopped'


async def sending():
    while True:
        msg = await q.get_next_message()
        await websocket.send(msg['text'])


async def receiving():
    while True:
        data = await websocket.receive()
        print(f'received: {data}')


@app.websocket('/ws')
async def ws():
    producer = asyncio.create_task(sending())
    consumer = asyncio.create_task(receiving())
    await asyncio.gather(producer, consumer)


def run_http_server():
    app.run(loop=loop)

