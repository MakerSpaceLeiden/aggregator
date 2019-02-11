import asyncio
import json
import logging
from functools import wraps, partial
from quart import Quart, websocket, request, Response, jsonify
import aiocron
from aggregator.communication import HttpServerInputMessageQueue, WorkerInputQueue
from quart.logging import default_handler, serving_handler

loop = asyncio.get_event_loop()


def get_input_message_queue():
    return HttpServerInputMessageQueue(loop)


def get_worker_input_queue():
    return WorkerInputQueue(loop)


def start_checking_for_stale_checkins(aggregator, worker_input_queue, crontab, logger):
    @aiocron.crontab(crontab)
    @asyncio.coroutine
    def early_in_the_morning():
        worker_input_queue.add_task(aggregator.clean_stale_user_checkins, logger)


def run_http_server(input_message_queue, aggregator, worker_input_queue, logger, basic_auth, host, port):
    # Configure Quart's internal logging
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    default_handler.setFormatter(formatter)
    serving_handler.setFormatter(formatter)

    logger = logger.getLogger(subsystem='http')

    def with_basic_auth(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not request.authorization or not (
                    request.authorization.username == basic_auth['username'] and
                    request.authorization.password == basic_auth['password']):
                realm = basic_auth['realm']
                logger.error(f'Wrong basi auth: username = {request.authorization.username}')
                return Response(
                    'Could not verify your access level for that URL.\n'
                    'You have to login with proper credentials', 401,
                    {'WWW-Authenticate': f'Basic realm="{realm}"'})
            return f(*args, **kwargs)
        return decorated

    # ------------------------------------

    app = Quart('aggregator')

    @app.route('/', methods=['GET'])
    async def root():
        return Response('MSL Aggregator', mimetype='text/plain')

    @app.route('/tags', methods=['GET'])
    @with_basic_auth
    async def tags():
        logger.info('GET tags')
        _tags = await worker_input_queue.add_task_with_result_future(aggregator.get_tags, logger)
        return jsonify({'tags': [{
            'tag_id': tag.tag_id,
            'tag': tag.tag,
            'user': tag.user.for_json(),
        } for tag in _tags]})

    @app.route('/space_state', methods=['GET'])
    @with_basic_auth
    async def space_state():
        logger.info('GET space_state')
        state = await worker_input_queue.add_task_with_result_future(aggregator.get_space_state_for_json, logger)
        return jsonify(state)

    @app.route('/telegram/token', methods=['POST'])
    @with_basic_auth
    async def telegram_token():
        logger.info('POST telegram_token')
        request_body = await request.get_data()
        request_payload = json.loads(request_body)
        token = await worker_input_queue.add_task_with_result_future(partial(aggregator.create_telegram_connect_token, request_payload['user_id']), logger)
        return Response(token.encode('utf-8'), mimetype='text/plain')

    # -- Web Socket -----

    # async def ws_sending():
    #     while True:
    #         msg = await input_message_queue.get_next_message()
    #         await websocket.send(msg['text'])
    #
    # async def ws_receiving():
    #     while True:
    #         data = await websocket.receive()
    #         print(f'received: {data}')
    #
    # @app.websocket('/ws')
    # async def ws():
    #     producer = asyncio.create_task(ws_sending())
    #     consumer = asyncio.create_task(ws_receiving())
    #     await asyncio.gather(producer, consumer)

    # -- Run server ----

    logger.info(f'HTTP+WS Server listening on {host}:{port}')

    # Blocks until Ctrl-C
    app.run(
        host=host,
        port=port,
        loop=loop,
        access_log_format="%(h)s %(r)s %(s)s %(b)s %(D)s",
    )

    logger.info('Signal intercepted. Stopping HTTP server.')
