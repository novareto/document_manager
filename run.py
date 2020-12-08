import os
import logging
import functools
import pathlib
import contextlib
import colorlog
from omegaconf import OmegaConf
from horseman.prototyping import WSGICallable


def make_logger(name, level=logging.DEBUG) -> logging.Logger:
    logger = colorlog.getLogger(name)
    logger.setLevel(level)
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(red)s%(levelname)-8s%(reset)s '
        '%(yellow)s[%(name)s]%(reset)s %(green)s%(message)s'))
    logger.addHandler(handler)
    return logger


@contextlib.contextmanager
def environment(**environ):
    """Temporarily set the process environment variables.
    """
    def cast_items(mapping):
        for k, v in mapping.items():
            v = str(v)
            if v.startswith('path:'):
                path = pathlib.Path(v[5:]).resolve()
                path.mkdir(parents=True, exist_ok=True)
                yield k, str(path)
            else:
                yield k, v

    old_environ = dict(os.environ)
    os.environ.update(dict(cast_items(environ)))
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_environ)


def webpush_plugin(config):
    from collections import namedtuple

    webpush = namedtuple(
        'Webpush', [
            'claims',
            'private_key',
            'public_key',
        ])

    with open(config.private_key) as fd:
        private_key = fd.readline().strip("\n")

    with open(config.public_key) as fd:
        public_key = fd.read().strip("\n")

    return webpush(
        private_key=private_key,
        public_key=public_key,
        claims=config.vapid_claims
    )


def api(config, connector, webpush, emailer):
    from docmanager.app import api as app
    app.connector = connector
    app.config.update(config)
    app.plugins.register(webpush, name="webpush")
    app.plugins.register(emailer, name="emailer")
    return app


def browser(config, connector, webpush, emailer):
    from docmanager.models import User
    from docmanager.mq import AMQPEmitter
    from docmanager.auth import Auth
    from docmanager.app import browser as app


    def fanstatic_middleware(config) -> WSGICallable:
        from fanstatic import Fanstatic
        return functools.partial(Fanstatic, **config)


    def session_middleware(config) -> WSGICallable:
        import cromlech.session
        import cromlech.sessions.file

        folder = pathlib.Path("/tmp/sessions")
        handler = cromlech.sessions.file.FileStore(folder, 3000)
        manager = cromlech.session.SignedCookieManager(
            "secret", handler, cookie="my_sid")
        return cromlech.session.WSGISessionManager(
            manager, environ_key=config.session)


    app.connector = connector
    app.config.update(config.app)

    app.plugins.register(webpush, name="webpush")
    app.plugins.register(emailer, name="emailer")

    db = connector.get_database()
    auth = Auth(db.bind(User), config.app.env)
    app.plugins.register(auth, name="authentication")
    app.middlewares.register(auth, order=0)  # very first.

    amqp = AMQPEmitter(config.amqp)
    app.plugins.register(amqp, name="amqp")

    app.middlewares.register(
        session_middleware(config.app.env), order=1)

    app.middlewares.register(
        fanstatic_middleware(config.app.assets), order=2)

    return app


def start(config):
    import bjoern
    import importscan

    import docmanager
    import docmanager.mq
    import uvcreha.example
    import uvcreha.example.app
    from reiter.arango.connector import Connector
    from rutter.urlmap import URLMap
    from docmanager.emailer import SecureMailer

    importscan.scan(docmanager)
    importscan.scan(uvcreha.example)

    logger = make_logger('docmanager')
    connector = Connector(**config.arango)
    webpush = webpush_plugin(config.webpush)
    emailer = SecureMailer(config.emailer)

    app = URLMap()
    app['/'] = browser(config, connector, webpush, emailer)
    app['/api'] = api(config, connector, webpush, emailer)

    # Serving the app
    AMQPworker = docmanager.mq.Worker(app, config.amqp)
    try:
        AMQPworker.start()

        logger.info(
            "Server started on "
            f"http://{config.server.host}:{config.server.port}")

        bjoern.run(
            app, config.server.host,
            int(config.server.port), reuse_port=True)
    except KeyboardInterrupt:
        pass
    finally:
        AMQPworker.stop()


def resolve_path(path):
    path = pathlib.Path(path)
    return path.resolve()


if __name__ == "__main__":
    OmegaConf.register_resolver("path", resolve_path)
    baseconf = OmegaConf.load('config.yaml')
    override = OmegaConf.from_cli()
    config = OmegaConf.merge(baseconf, override)
    with environment(**config.environ):
        start(config)
