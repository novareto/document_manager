import abc
from datetime import datetime
from pkg_resources import iter_entry_points

from arango.exceptions import DocumentGetError
from pydantic import BaseModel, Field

from docmanager.request import Request


class ProtectedModel(abc.ABC):

    __permissions__: list

    @abc.abstractmethod
    def __check_security__(self, request: Request):
        pass


class Base(BaseModel):
    name: str
    content_type: str
    mod_date: datetime = Field(default_factory=datetime.utcnow)
    state: str #ENUM

    @classmethod
    def instanciate(cls, request: Request, docid: str, **bindable):
        connector = request.app.db.connector
        documents = connector.collection('documents')
        if (docdata := documents.get(docid)) is not None:
            return cls(**docdata)
        raise LookupError(f'Document {docid} is unknown.')


class User(BaseModel):
    username: str
    password: str

    @classmethod
    def instanciate(cls, request: Request, userid: str, **bindable):
        connector = request.app.db.connector
        users = connector.collection('users')
        if (userdata := users.get(userid)) is not None:
            return cls(**userdata)
        raise LookupError(f'User {userid} is unknown.')


class Document(BaseModel):
    body: str


class ModelsRegistry(dict):
    __slots__ = ()

    def register(self, name, model):
        if name in self:
            raise KeyError(f'Model {name} already exists.')
        if not issubclass(model, BaseModel):
            raise ValueError(f'Model {name} is not a valid pydatic model.')
        self[name] = model

    def load(self):
        self.clear()
        for loader in iter_entry_points('docmanager.models'):
            self.register(loader.name, loader.load())
