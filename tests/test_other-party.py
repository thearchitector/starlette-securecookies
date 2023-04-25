import pytest
from itsdangerous import BadSignature, TimestampSigner
from starlette.middleware import Middleware, sessions


def test_third_party(client_factory, fernet):
    # cookies added by other middleware should get (de/en)crypted correctly
    middleware = [Middleware(sessions.SessionMiddleware, secret_key="verysecretsecret")]

    ## set a session cookie
    response = client_factory(middleware=middleware).get("/session")
    assert response.status_code == 200

    ### it should be encrypted / will have an invalid sig
    scookie = response.cookies["session"]
    with pytest.raises(BadSignature):
        TimestampSigner("verysecretsecret").unsign(scookie.encode())
    TimestampSigner("verysecretsecret").unsign(fernet.decrypt(scookie.encode()))

    ## read a session cookie, should be decrypted / will have a valid sig
    client_factory(middleware=middleware, cookies={"session": scookie}).get(
        "/session_val"
    )
