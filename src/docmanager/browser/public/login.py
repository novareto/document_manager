from pathlib import Path

import wtforms.form
import wtforms.fields
import wtforms.validators
from chameleon import PageTemplateLoader

import horseman.response
from horseman.meta import APIView
from docmanager.request import Request
from docmanager.app import application
from docmanager.browser.layout import template


TEMPLATES = PageTemplateLoader(
    str((Path(__file__).parent / 'templates').resolve()), ".pt")


class LoginForm(wtforms.form.Form):

    username = wtforms.fields.StringField(
        'Username',
        validators=(wtforms.validators.InputRequired(),)
    )

    password = wtforms.fields.PasswordField(
        'Password',
        validators=(wtforms.validators.InputRequired(),)
    )


@application.routes.register('/login')
class LoginView(APIView):

    @template(TEMPLATES['login.pt'], raw=False)
    def GET(self, request: Request):
        form = LoginForm()
        return {'form': form, 'error': None, 'path': request.route.path}

    @template(TEMPLATES['login.pt'], raw=False)
    def POST(self, request: Request):
        form = LoginForm(request.data['form'])
        if not form.validate():
            return {'form': form, 'error': 'form'}
        if (userdata := request.app['auth'].from_credentials(
                request.data['form'].to_dict())) is not None:
            user = request.app.models['user'](**userdata)
            request.app['auth'].remember(request.environ, user)
            print('The login was successful')
            return horseman.response.Response.create(
                302, headers={'Location': '/'})
        return {'form': form, 'error': 'auth', 'path': request.route.path}


@application.routes.register('/logout')
def LogoutView(request: Request):
    request.session.store.clear(request.session.sid)
    return horseman.response.Response.create(
            302, headers={'Location': '/'})
