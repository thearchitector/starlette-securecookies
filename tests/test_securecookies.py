import pytest

from securecookies import BadArgumentError


def test_overconstrained(client_factory):
    with pytest.raises(BadArgumentError, match="doesn't make sense"):
        client = client_factory(included_cookies=["some"], excluded_cookies=["none"])
        client.get("/get")


def test_bad_samesite(client_factory):
    client = client_factory(cookie_samesite="strict")
    client.get("/get")

    with pytest.raises(BadArgumentError, match="SameSite"):
        client = client_factory(cookie_samesite="invalid")
        client.get("/get")


def test_outgoing(client_factory, fernet):
    # api write ginger-molasses, client needs to decrypt
    response = client_factory().get("/get")
    assert response.status_code == 200

    cookie = response.cookies["type"]
    assert fernet.decrypt(cookie.encode()).decode() == "ginger-molasses"
    assert not next(iter(response.cookies.jar)).secure


def test_outgoing_complex(client_factory, fernet):
    # api write ginger-molasses overwrites secure=True, client needs to decrypt
    client = client_factory(cookie_secure=True)
    response = client.get("/get")
    assert response.status_code == 200

    cookie = response.cookies["type"]
    assert fernet.decrypt(cookie.encode()).decode() == "ginger-molasses"
    assert next(iter(response.cookies.jar)).secure


def test_outgoing_included(client_factory, fernet):
    # only type should be encrypted
    client = client_factory(included_cookies=["type"])
    response = client.get("/getm")

    assert response.status_code == 200
    assert (
        fernet.decrypt(response.cookies["type"].encode()).decode() == "ginger-molasses"
    )
    assert response.cookies["anothertype"] == "chocolate-chip"


def test_outgoing_excluded(client_factory, fernet):
    # type should not be encrypted
    client = client_factory(excluded_cookies=["type"])
    response = client.get("/getm")
    assert response.status_code == 200

    cookie = response.cookies["anothertype"]
    assert fernet.decrypt(cookie.encode()).decode() == "chocolate-chip"
    assert response.cookies["type"] == "ginger-molasses"


def test_incoming(client_factory, mock_cookies, fernet):
    # client passes encrypted, should validate if decrypted in middleware
    client = client_factory(cookies=mock_cookies)
    response = client.get("/validate")
    assert response.status_code == 200

    cookie = response.cookies["topsecret"]
    assert fernet.decrypt(cookie.encode()).decode() == "iateyoursecret"


def test_incoming_included(client_factory, mock_cookies, fernet):
    # don't discard insecure, so should be able to read value
    client = client_factory(
        cookies=mock_cookies,
        included_cookies=["topsecret", "othercookie"],
        discard_invalid=False,
    )
    response = client.get("/validate")
    assert response.status_code == 200

    topsecret = response.cookies["topsecret"]
    othercookie = response.cookies["othercookie"]
    assert fernet.decrypt(topsecret.encode()).decode() == "iateyoursecret"
    assert fernet.decrypt(othercookie.encode()).decode() == "notreallyasecret"


def test_incoming_included_discarded(client_factory, mock_cookies, fernet):
    # do discard insecure, so shouldn't be able to read value
    client = client_factory(
        cookies=mock_cookies, included_cookies=["topsecret", "othercookie"]
    )
    response = client.get("/validate")
    assert response.status_code == 200

    topsecret = response.cookies["topsecret"]
    assert fernet.decrypt(topsecret.encode()).decode() == "iateyoursecret"
    assert "othercookie" not in response.cookies


def test_incoming_excluded(client_factory, mock_cookies, fernet):
    # excluding secure cookie means validation should fail
    client = client_factory(cookies=mock_cookies, excluded_cookies=["topsecret"])

    with pytest.raises(AssertionError, match="thisisasecretcookie"):
        client.get("/validate")
