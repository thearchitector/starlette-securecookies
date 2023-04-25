from starlette.middleware import Middleware
from starlette_csrf import CSRFMiddleware

from securecookies.extras.csrf import SecureCSRFMiddleware


def test_csrf_bad_vanilla(client_factory):
    # check if normal CSRF fails. it should since the token header is not decrypted
    # by default
    client = client_factory(
        middleware=[Middleware(CSRFMiddleware, secret="verysecretsecret")]
    )
    response = client.post(
        "/post",
        headers={"x-csrftoken": client.get("/get").cookies["csrftoken"]},
        json={"hello": "world"},
    )
    assert response.status_code == 403


def test_csrf_secure(client_factory):
    # check if the secure CSRF works. it should automatically find the secure cookie
    # middleware and decrypt the header.
    client = client_factory(
        middleware=[Middleware(SecureCSRFMiddleware, secret="verysecretsecret")]
    )
    response = client.post(
        "/post",
        headers={"x-csrftoken": client.get("/get").cookies["csrftoken"]},
        json={"hello": "world"},
    )
    assert response.status_code == 200
