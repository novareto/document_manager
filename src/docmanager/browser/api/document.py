import horseman.response
from docmanager.app import application
from docmanager.request import Request
from docmanager.db import Document


@application.route(
    '/users/{username}/files/{fileid}/doc.add',
    methods=['POST', 'PUT'])
def doc_add(request: Request, username: str, fileid: str):
    data = request.extract()
    form = data['form'].dict()
    model = Document(request.app.database)
    document = model.create(username=username, az=fileid, **form)
    return horseman.response.Response.from_json(201, body=document.json())


@application.route(
    '/users/{username}/files/{fileid}/docs/{docid}',
    methods=['GET'])
def doc_view(request: Request, username: str, fileid: str, docid: str):
    model = Document(request.app.database)
    document = model.find_one(_key=docid, az=fileid, username=username)
    if document is None:
        return horseman.response.reply(404)
    return horseman.response.Response.from_json(200, body=document.json())


@application.route(
    '/users/{username}/files/{fileid}/docs/{docid}',
    methods=['DELETE'])
def doc_delete(request: Request, username: str, fileid: str, docid: str):
    model = Document(request.app.database)
    if model.find_one( _key=docid, az=fileid, username=username) is None:
        return horseman.response.reply(404)
    model.delete(docid)
    return horseman.response.reply(202)
