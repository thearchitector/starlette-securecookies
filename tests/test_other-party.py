import pytest
from itsdangerous import BadSignature, TimestampSigner


def test_third_party(client_factory, fernet):
    # cookies added by other middlewares should get (de/en)crypted correctly
    ## set a session cookie
    response = client_factory().get("/session")
    assert response.status_code == 200

    ### it should be encrypted / will have an invalid sig
    scookie = response.cookies["session"]
    with pytest.raises(BadSignature):
        TimestampSigner("verysecretsecret").unsign(scookie.encode())
    TimestampSigner("verysecretsecret").unsign(fernet.decrypt(scookie.encode()))

    ## read a session cookie, should be decrypted / will have a valid sig
    client_factory(cookies={"session": scookie}).get("/session_val")
