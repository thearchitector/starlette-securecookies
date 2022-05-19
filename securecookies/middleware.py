from http.cookies import SimpleCookie
from typing import List, Optional

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class BadArgumentError(Exception):
    """
    Generic error arguments with invalid values, or combinations of conflicting
    arguments.
    """


class SecureCookiesMiddleware(BaseHTTPMiddleware):
    """
    Provides automatic secure cookie support through symmetric Fernet encryption. As per
    the `cryptography` docs, security is achieved through:

    - 128-bit key AES in CBC mode using PKCS7 padding for encryption
    - HMAC using SHA256 for authentication.
    """

    secrets: List[str]
    """
    A list of secrets to use when encrypting and decrypting secure cookies. Supplying
    multiple secrets enables the use of key rotation, whereby the first key is used for
    all encryption, including to re-encrypt cookies previously encrypted with any of
    the other list entries.
    """

    def __init__(
        self,
        app: ASGIApp,
        secrets: List[str],
        discard_invalid: bool = True,
        cookie_path: Optional[str] = None,
        cookie_domain: Optional[str] = None,
        cookie_secure: Optional[bool] = None,
        cookie_httponly: Optional[bool] = None,
        cookie_samesite: Optional[str] = None,
        excluded_cookies: Optional[List[str]] = None,
        included_cookies: Optional[List[str]] = None,
    ) -> None:
        super().__init__(app)
        self.mfernet = MultiFernet(Fernet(s) for s in secrets)
        self.discard_invalid = discard_invalid
        """ Discard any invalid / unencrypted cookies present in the request."""
        self.cookie_path = cookie_path
        """ The Path field value to override on every cookie."""
        self.cookie_domain = cookie_domain
        """ The Domain field value to override on every cookie."""
        self.cookie_secure = cookie_secure
        """ The Secure field value to override on every cookie."""
        self.cookie_httponly = cookie_httponly
        """ The HttpOnly field value to override on every cookie."""
        self.cookie_samesite = cookie_samesite
        """ The SameStime field value to override on every cookie."""
        self.excluded_cookies = excluded_cookies
        """
        The list of cookies to ignore when decrypting and encrypting in
        the request --> response cycle. This option is mutually exclusive with
        `included_cookies`.
        """
        self.included_cookies = included_cookies
        """
        The list of cookies to decrypt and encrypt in the request --> response cycle.
        This option is mutually exclusive with `excluded_cookies`.
        """

        if excluded_cookies and included_cookies:
            raise BadArgumentError(
                "It doesn't make sense to specify both excluded and included cookies."
                " Supply with `excluded_cookies` or `included_cookies` to restrict"
                " which cookies should be secure."
            )

        if cookie_samesite and cookie_samesite.lower() not in ["strict", "lax", "none"]:
            raise BadArgumentError(
                "SameSite attribute must be either 'strict', 'lax' or 'none'"
            )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # request cookies are only passed along and mutable within the asgi scope
        headers = request.scope["headers"]
        raw_cookies = [h for h in headers if h[0] == b"cookie"]
        if len(raw_cookies):
            # if encrypted cookies are present, remove and parse them
            headers.remove(raw_cookies[0])
            cookies: SimpleCookie = SimpleCookie(raw_cookies[0][1].decode())

            for cookie, morsel in list(cookies.items()):
                # if the cookie is included or not excluded
                if (
                    (not self.included_cookies and not self.excluded_cookies)
                    or (self.included_cookies and cookie in self.included_cookies)
                    or (self.excluded_cookies and cookie not in self.excluded_cookies)
                ):
                    try:
                        # try to decrypt the token. if you can, then it's already
                        # encrypted and can be passed along
                        cookies[cookie] = self.mfernet.decrypt(
                            morsel.value.encode()
                        ).decode()
                    except InvalidToken:
                        # delete invalid or unencrypted cookies if enabled
                        if self.discard_invalid:
                            del cookies[cookie]

            # serialize and append the decrypted cookies to the asgi scope headers
            new_cookie = (
                b"cookie",
                cookies.output(header="", sep=";").strip().encode(),
            )
            headers.append(new_cookie)

        # propagate the modified request
        response: Response = await call_next(request)

        # for every cookie in the response
        for raw_cookie in response.headers.getlist("set-cookie"):
            # decode it
            ncookie: SimpleCookie = SimpleCookie(raw_cookie)
            key = [*ncookie.keys()][0]

            # if the cookie is included or not excluded
            if (
                (not self.included_cookies and not self.excluded_cookies)
                or (self.included_cookies and key in self.included_cookies)
                or (self.excluded_cookies and key not in self.excluded_cookies)
            ):
                # create a new encrypted cookie with the desired attributes
                response.set_cookie(
                    key,
                    value=self.mfernet.encrypt(ncookie[key].value.encode()).decode(),
                    path=self.cookie_path or ncookie[key]["path"],
                    domain=self.cookie_domain or ncookie[key]["domain"],
                    secure=self.cookie_secure or ncookie[key]["secure"],
                    httponly=self.cookie_httponly or ncookie[key]["httponly"],
                    samesite=self.cookie_samesite or ncookie[key]["samesite"],
                )

        return response
