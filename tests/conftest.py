import pytest
from cryptography.fernet import Fernet
from securecookies import SecureCookiesMiddleware
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient


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
    response.set_cookie(
        "topsecret", request.cookies.get("othercookie", "iateyoursecret")
    )
    return response


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
    def _func(**kwargs):
        return TestClient(
            Starlette(
                debug=True,
                routes=[
                    Route("/get", _get, methods=["GET"]),
                    Route("/getm", _get_multi, methods=["GET"]),
                    Route("/validate", _validate, methods=["GET"]),
                ],
                middleware=[
                    Middleware(SecureCookiesMiddleware, secrets=[secret], **kwargs)
                ],
            )
        )

    yield _func


@pytest.fixture
def client(secret, client_factory):
    yield client_factory()
