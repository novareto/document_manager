import hydra
import colorlog
import logging
import threading
from pathlib import Path
from functools import partial
from kombu.mixins import ConsumerMixin
from kombu import Exchange, Queue, Consumer


class MyConsumer(Consumer):

    def receive(self, body, message):
        print('I AM CALLED')


class Worker(ConsumerMixin):

    def __init__(self, connection, app, logger):
        self.connection = connection
        self.app = app
        self.logger = logger
        self.exchange = Exchange('object_events', type='topic')
        self.queues = dict(
            add_q=Queue(
                'add', self.exchange, routing_key='object.add'),
            del_q=Queue(
                'delete', self.exchange, routing_key='object.delete'),
            upd_q=Queue(
                'update', self.exchange, routing_key='object.update'),
        )

    def get_consumers(self, Consumer, channel):
        Consumer = partial(
            MyConsumer, channel, on_decode_error=self.on_decode_error)
        return [
            Consumer(
                queues=(self.queues['add_q'], self.queues['upd_q']),
                accept=['pickle', 'json'])
        ]

    def process_task(self, body, message):
        self.logger.info("Got task body: %s", body)
        self.logger.info("Got task Message: %s", message)
        message.ack()

    def runner(self):
        with Connection(config.amqp.url) as conn:
            self.run()

    def start(cls, app, config, logger):
        worker = cls(conn, app, logger)
        thread = threading.Thread(target=worker.runner)
        thread.start()
        return thread
