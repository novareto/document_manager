import horseman.response
import horseman.meta
from horseman.http import Multidict
from reiter.form import trigger
from reiter.routing.predicate_route import BranchingView, PredicateError
from docmanager.app import browser
from docmanager.browser.form import Form, FormView
from docmanager.browser.layout import template, TEMPLATES
from docmanager.browser.openapi import generate_doc
from docmanager.models import User, UserPreferences, File, Document
from docmanager.request import Request
from docmanager.workflow import user_workflow


@browser.routes.register("/doc")
@template(TEMPLATES["swagger.pt"], raw=False)
def doc_swagger(request: Request):
    return {"url": "/openapi.json"}


@browser.routes.register("/openapi.json")
def openapi(request: Request):
    open_api = generate_doc(request.app.routes)
    return horseman.response.reply(
        200,
        body=open_api.json(by_alias=True, exclude_none=True, indent=2),
        headers={"Content-Type": "application/json"}
    )


@browser.route("/")
class LandingPage(horseman.meta.APIView):

    @template(TEMPLATES["index.pt"], layout_name="default", raw=False)
    def GET(self, request: Request):
        user = request.user
        return dict(request=request, user=user, view=self)

    def get_files(self, request, key):
        return request.database(File).find(username=key)

    def get_documents(self, request, username, az):

        return request.database(Document).find(username=username, az=az)


@browser.route("/webpush")
@template(TEMPLATES["webpush.pt"], layout_name="default", raw=False)
def webpush(request: Request):
    return dict(request=request)


def condition_is_test(request):
    if request.route.params['condition'] != 'test':
        raise PredicateError.create(400, 'Condition must be test')


@browser.route("/branching/{condition}", methods=['GET'])
class Branch(BranchingView):
    pass


@Branch.register(['GET'], condition_is_test)
def test_branching(request: Request, condition):
    return horseman.response.reply(200, "Yeah, i'm a test")


@Branch.register(['GET'])
def test_other_branching(request: Request, condition):
    return horseman.response.reply(
        200, "Yeah, i'm not the test, but a default")


@browser.route("/preferences")
class EditPreferences(FormView):

    title = "E-Mail Adresse ändern"
    description = "Edit your preferences."
    action = "preferences"
    model = UserPreferences

    @trigger("abbrechen", "Abbrechen", css="btn btn-secondary")
    def abbrechen(self, request):
        pass

    @trigger("update", "Update", css="btn btn-primary")
    def update(self, request):
        data = request.extract()["form"]
        form = self.setupForm(formdata=data)
        if not form.validate():
            return {
                "form": form,
                "view": self,
                "error": None,
                "path": request.route.path
            }

        user = User(request.db_session)
        user.update(request.user.key, preferences=data.dict())
        return horseman.response.reply(200)

    @template(TEMPLATES["base_form.pt"], layout_name="default", raw=False)
    def GET(self, request: Request):
        preferences = request.user.preferences.dict()
        form = self.setupForm(data=preferences)
        return {
            "form": form,
            "view": self,
            "error": None,
            "path": request.route.path
        }


@browser.route("/register")
class RegistrationForm(FormView):

    title = "Registration"
    description = "Finish your registration"
    action = "/register"
    model = User

    def setupForm(self, data={}, formdata=Multidict()):
        form = Form.from_model(
            self.model, only=("email",), email={
                'required': True
            })
        form.process(data=data, formdata=formdata)
        return form

    @trigger("register", "Register", css="btn btn-primary")
    def register(self, request, data):
        form = self.setupForm(
            data=request.user.dict(), formdata=data.form
        )
        if not form.validate():
            return {
                "form": form,
                "view": self,
                "error": None,
                "path": request.route.path
            }

        request.user.email = form.data['email']
        wf = user_workflow(request.user)
        wf.set_state(user_workflow.states.active)
        request.user.save()

        return horseman.response.Response.create(
            302, headers={"Location": "/"}
        )
