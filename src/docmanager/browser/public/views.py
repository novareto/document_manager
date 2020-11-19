from horseman.response import Response
from docmanager.app import browser
from docmanager.request import Request
from docmanager.browser.layout import template, TEMPLATES
from docmanager.db import User


@browser.route("/")
@template(TEMPLATES["index.pt"], layout_name="default", raw=False,)
def user(request: Request):
    request.flash().add(body="BLA BLUB")
    user = User(request.db_session)
    return dict(request=request, user=user)
