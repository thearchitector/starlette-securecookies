import pytest
from cryptography.fernet import Fernet
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from securecookies import SecureCookiesMiddleware


async def _get(request):
    # set a simple cookie
    response = PlainTextResponse("Hello world!")
    response.set_cookie("type", "ginger-molasses", secure=False)
    return response


async def _get_multi(request):
    # set 2 simple cookies
    response = PlainTextResponse("Hello world!")
    response.set_cookie("type", "ginger-molasses")
    response.set_cookie("anothertype", "chocolate-chip")
    return response


async def _validate(request):
    # check an incoming cookie, modify and return it
    assert request.cookies.get("topsecret") == "thisisasecretcookie"

    response = PlainTextResponse("Hello world!")

    response.set_cookie("topsecret", "iateyoursecret")
    if request.cookies.get("othercookie"):
        response.set_cookie("othercookie", request.cookies.get("othercookie"))

    return response


async def _session(request):
    # set a session variable, expect SessionMiddleware to encode & sign it
    # then SecureCookies to encrypt it
    request.session["banana"] = "hello"
    return PlainTextResponse("Session set")


async def _validate_session(request):
    # read a session variable, expect SecureCookies to decrypt it
    # then SessionMiddleware to unsign & decode it
    assert request.session["banana"] == "hello"
    return PlainTextResponse("Session get")


async def _post(request):
    await request.json()
    return PlainTextResponse("JSON post")


@pytest.fixture(scope="session")
def secret():
    yield Fernet.generate_key()


@pytest.fixture(scope="session")
def fernet(secret):
    yield Fernet(secret)


@pytest.fixture(scope="session")
def mock_cookies(fernet):
    yield {
        "topsecret": fernet.encrypt(b"thisisasecretcookie").decode(),
        "othercookie": "notreallyasecret",
    }


@pytest.fixture(scope="session")
def client_factory(secret):
    def _func(cookies=None, middleware=None, **kwargs):
        return TestClient(
            Starlette(
                debug=True,
                routes=[
                    Route("/get", _get, methods=["GET"]),
                    Route("/getm", _get_multi, methods=["GET"]),
                    Route("/validate", _validate, methods=["GET"]),
                    # third party
                    Route("/session", _session, methods=["GET"]),
                    Route("/session_val", _validate_session, methods=["GET"]),
                    # csrf
                    Route("/post", _post, methods=["POST"]),
                ],
                middleware=[
                    # secure cookies must be first in the list so it can decrypt first
                    # and encrypt last
                    Middleware(SecureCookiesMiddleware, secrets=[secret], **kwargs),
                    *(middleware or []),
                ],
            ),
            cookies=cookies,
        )

    yield _func
