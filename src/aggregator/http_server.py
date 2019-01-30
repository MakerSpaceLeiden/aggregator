import asyncio
from functools import wraps
from quart import Quart, websocket, request, Response, jsonify
from aggregator.communication import HttpServerInputMessageQueue, WorkerInputQueue

loop = asyncio.get_event_loop()


def get_input_message_queue():
    return HttpServerInputMessageQueue(loop)


def get_worker_input_queue():
    return WorkerInputQueue(loop)


def run_http_server(input_message_queue, aggregator, worker_input_queue, logger, basic_auth, host, port):
    logger = logger.getLogger(subsystem='http')

    def with_basic_auth(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not request.authorization or not (
                    request.authorization.username == basic_auth['username'] and
                    request.authorization.password == basic_auth['password']):
                realm = basic_auth['realm']
                return Response(
                    'Could not verify your access level for that URL.\n'
                    'You have to login with proper credentials', 401,
                    {'WWW-Authenticate': f'Basic realm="{realm}"'})
            return f(*args, **kwargs)
        return decorated

    # ------------------------------------

    app = Quart('aggregator')

    @app.route('/')
    async def hello():
        return 'MSL Aggregator'

    @app.route('/tags')
    @with_basic_auth
    async def tags():
        logger.info('GET tags')
        _tags = await worker_input_queue.add_task_with_result_future(aggregator.get_tags, logger)
        return jsonify({'tags': [{
            'tag_id': tag.tag_id,
            'tag': tag.tag,
            'user': tag.user._asdict(),
        } for tag in _tags]})

    # -- Web Socket -----

    async def ws_sending():
        while True:
            msg = await input_message_queue.get_next_message()
            await websocket.send(msg['text'])

    async def ws_receiving():
        while True:
            data = await websocket.receive()
            print(f'received: {data}')

    @app.websocket('/ws')
    async def ws():
        producer = asyncio.create_task(ws_sending())
        consumer = asyncio.create_task(ws_receiving())
        await asyncio.gather(producer, consumer)

    # -- Run server ----

    logger.info(f'HTTP+WS Server listening on {host}:{port}')
    app.run(
        host=host,
        port=port,
        loop=loop,
    )
