import pytest
from securecookies import BadArgumentError


def test_overcontrained(client_factory):
    with pytest.raises(BadArgumentError, match="doesn't make sense"):
        client_factory(included_cookies=["some"], excluded_cookies=["none"])


def test_bad_samesite(client_factory):
    client_factory(cookie_samesite="strict")

    with pytest.raises(BadArgumentError, match="SameSite"):
        client_factory(cookie_samesite="invalid")


def test_outgoing(client, fernet):
    # api write ginger-molasses, client needs to decrypt
    response = client.get("/get")

    assert response.status_code == 200
    cookie = [*response.cookies][0]
    assert fernet.decrypt(cookie.value.encode()).decode() == "ginger-molasses"
    assert not cookie.secure


def test_outgoing_complex(client_factory, fernet):
    # api write ginger-molasses overwrites secure=True, client needs to decrypt
    client = client_factory(cookie_secure=True)
    response = client.get("/get")

    assert response.status_code == 200
    cookie = [*response.cookies][0]
    assert fernet.decrypt(cookie.value.encode()).decode() == "ginger-molasses"
    assert cookie.secure


def test_outgoing_included(client_factory, fernet):
    # only type should be encrypted
    client = client_factory(included_cookies=["type"])
    response = client.get("/getm")

    assert response.status_code == 200
    cookies = [*response.cookies]
    print(cookies)
    assert cookies[0].name == "anothertype"
    assert cookies[1].name == "type"
    assert cookies[0].value == "chocolate-chip"
    assert fernet.decrypt(cookies[1].value.encode()).decode() == "ginger-molasses"


def test_outgoing_excluded(client_factory, fernet):
    # type should not be encrypted
    client = client_factory(excluded_cookies=["type"])
    response = client.get("/getm")

    assert response.status_code == 200
    cookies = [*response.cookies]
    assert cookies[0].name == "anothertype"
    assert cookies[1].name == "type"
    assert fernet.decrypt(cookies[0].value.encode()).decode() == "chocolate-chip"
    assert cookies[1].value == "ginger-molasses"


def test_incoming(client, mock_cookies, fernet):
    # client passes encrypted, should validate if decrypted in middleware
    response = client.get("/validate", cookies=mock_cookies)

    assert response.status_code == 200
    assert (
        fernet.decrypt([*response.cookies][0].value.encode()).decode()
        == "iateyoursecret"
    )


def test_incoming_included(client_factory, mock_cookies, fernet):
    # don't discard insecure, so should be able to read value
    client = client_factory(
        included_cookies=["topsecret", "othercookie"], discard_invalid=False
    )
    response = client.get("/validate", cookies=mock_cookies)

    assert response.status_code == 200
    assert (
        fernet.decrypt([*response.cookies][0].value.encode()).decode()
        == "notreallyasecret"
    )


def test_incoming_included_fail(client_factory, mock_cookies, fernet):
    # do discard insecure, so shouldn't be able to read value
    client = client_factory(included_cookies=["topsecret", "othercookie"])
    response = client.get("/validate", cookies=mock_cookies)

    assert response.status_code == 200
    assert (
        fernet.decrypt([*response.cookies][0].value.encode()).decode()
        == "iateyoursecret"
    )


def test_incoming_excluded(client_factory, mock_cookies, fernet):
    # excluding secure cookie means validation should fail
    client = client_factory(excluded_cookies=["topsecret"])

    with pytest.raises(AssertionError, match="thisisasecretcookie"):
        client.get("/validate", cookies=mock_cookies)
