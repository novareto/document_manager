import functools
import fanstatic
import cromlech.session
import cromlech.sessions.file
import horseman.http
import horseman.meta
import horseman.response
import reiter.view.meta

import json
from typing import Optional
from dataclasses import dataclass, field
from fs.osfs import OSFS
from horseman.types import WSGICallable
from reiter.amqp.emitter import AMQPEmitter
from reiter.application.app import Application
from reiter.application.browser import registries
from reiter.arango.connector import Connector
from reiter.arango.validation import ValidationError
from roughrider.routing.route import NamedRoutes
from roughrider.storage.meta import StorageCenter
from uvcreha.auth import Auth
from uvcreha.emailer import SecureMailer
from uvcreha.models import JSONSchemaRegistry
from uvcreha.request import Request
from uvcreha.security import SecurityError
from uvcreha.webpush import Webpush
from repoze.vhm.middleware import VHMExplicitFilter
from twilio.rest import Client


def repoze_filter(config) -> WSGICallable:
    return functools.partial(VHMExplicitFilter, **config)


def fanstatic_middleware(config) -> WSGICallable:
    return functools.partial(fanstatic.Fanstatic, **config)


def session_middleware(config) -> WSGICallable:
    handler = cromlech.sessions.file.FileStore(
        config.session.cache, 3000
    )
    manager = cromlech.session.SignedCookieManager(
        config.session.cookie_secret,
        handler,
        cookie=config.session.cookie_name
    )
    return cromlech.session.WSGISessionManager(
        manager, environ_key=config.env.session)


def webpush_plugin(config):

    with open(config.private_key) as fd:
        private_key = fd.readline().strip("\n")

    with open(config.public_key) as fd:
        public_key = fd.read().strip("\n")

    return Webpush(
        private_key=private_key,
        public_key=public_key,
        claims=config.vapid_claims
    )


def twilio_plugin(config):
    return Client(config.account_sid, config.auth_token)


class Routes(NamedRoutes):

    def __init__(self):
        super().__init__(extractor=reiter.view.meta.routables)


@dataclass
class RESTApplication(Application):

    connector: Optional[Connector] = None
    request_factory: horseman.meta.Overhead = Request

    def __call__(self, environ, start_response):
        try:
            if self._caller is not None:
                return self._caller(environ, start_response)
            return super().__call__(environ, start_response)
        except ValidationError as exc:
            return exc(environ, start_response)

    def configure(self, config):
        self.config.update(config.app)
        self.connector = Connector(**config.arango)
        self.request = self.config.factories.request

        # Utilities
        if config.emailer:
            emailer = SecureMailer(config.emailer)
            self.utilities.register(emailer, name="emailer")

        if config.webpush:
            webpush = webpush_plugin(config.webpush)
            self.utilities.register(webpush, name="webpush")

        if config.twilio:
            twilio = twilio_plugin(config.twilio)
            self.utilities.register(twilio, 'twilio')


@dataclass
class Browser(RESTApplication):

    routes: NamedRoutes = field(default_factory=Routes)
    ui: registries.UIRegistry = field(
        default_factory=registries.UIRegistry)

    def check_permissions(self, route, environ):
        if permissions := route.extras.get('permissions'):
            user = environ.get(self.config.env.user)
            if user is None:
                raise SecurityError(None, permissions)
            if not permissions.issubset(user.permissions):
                raise SecurityError(user, permissions - user.permissions)

    def configure(self, config):
        self.config.update(config.app)
        self.connector = Connector(**config.arango)
        self.request = self.config.factories.request

        # register JSON schemas
        with OSFS(config.app.storage.schemas) as fs:
            for schema in fs.listdir('/'):
                if schema.endswith('.json'):
                    with fs.open(schema) as fd:
                        data = json.load(fd)
                        JSONSchemaRegistry.register(data, data['name'])

        # utilities
        db = self.connector.get_database()
        auth = Auth(db(self.config.factories.user), self.config.env)
        self.utilities.register(auth, name="authentication")
        self.utilities.register(AMQPEmitter(config.amqp), name="amqp")
        self.utilities.register(StorageCenter(), name="storage")

        if config.emailer:
            emailer = SecureMailer(config.emailer)
            self.utilities.register(emailer, name="emailer")

        if config.webpush:
            webpush = webpush_plugin(config.webpush)
            self.utilities.register(webpush, name="webpush")

        if config.app.twilio:
            twilio = twilio_plugin(config.app.twilio)
            self.utilities.register(twilio, 'twilio')

        # middlewares
        self.register_middleware(repoze_filter(self.config.vhm), order=5)

        self.register_middleware(
            fanstatic_middleware(self.config.assets), order=10)

        self.register_middleware(
            session_middleware(self.config), order=20)

        self.register_middleware(auth, order=30)


api = RESTApplication(name='REST Application')
browser = Browser(name='Browser Application')
