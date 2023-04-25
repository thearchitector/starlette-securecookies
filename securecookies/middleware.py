import sys
from http.cookies import SimpleCookie
from typing import Any, List, Optional

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal


class BadArgumentError(Exception):
    """
    Generic error arguments with invalid values, or combinations of conflicting
    arguments.
    """


class SecureCookiesMiddleware(BaseHTTPMiddleware):
    """
    Provides automatic secure cookie support through symmetric Fernet encryption. As per
    the `cryptography` docs, security is achieved through:

    - 128-bit key AES in CBC mode using PKCS7 padding for encryption.
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
        cookie_samesite: Optional[Literal["strict", "lax", "none"]] = None,
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
                " Supply either `excluded_cookies` or `included_cookies` to restrict"
                " which cookies should be secure."
            )

        if cookie_samesite and cookie_samesite.lower() not in ["strict", "lax", "none"]:
            raise BadArgumentError(
                "SameSite attribute must be either 'strict', 'lax' or 'none'"
            )

    def set_header(self, request: Request, header: str, value: str) -> None:
        """
        Adds the given Header to the available Request headers. If the Header already
        exists, its value is overwritten.
        """
        hkey = header.encode("latin-1")
        request.scope["headers"] = [
            *(h for h in request.scope["headers"] if h[0] != hkey),
            (hkey, value.encode("latin-1")),
        ]

    def decrypt(self, value: str) -> str:
        """Decrypt the given value using any of the configured secrets."""
        return self.mfernet.decrypt(value.encode()).decode()

    def encrypt(self, value: str) -> str:
        """Encrypt the given value using the first configured secret."""
        return self.mfernet.encrypt(value.encode()).decode()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if len(request.cookies):
            cookies: SimpleCookie[Any] = SimpleCookie()
            for cookie, value in request.cookies.items():
                # if the cookie is included or not excluded
                if (
                    (not self.included_cookies and not self.excluded_cookies)
                    or (self.included_cookies and cookie in self.included_cookies)
                    or (self.excluded_cookies and cookie not in self.excluded_cookies)
                ):
                    try:
                        # try to decrypt the cookie and pass it along
                        cookies[cookie] = self.decrypt(value)
                    except InvalidToken:
                        # delete invalid or unencrypted cookies unless disabled
                        if not self.discard_invalid:
                            cookies[cookie] = value

            # serialize and set the decrypted cookies to the asgi scope headers
            # we have to modify the scope directly because request objects are not
            # passed between ASGI applications / middleware.
            self.set_header(
                request, "cookie", cookies.output(header="", sep=";").strip()
            )

        # propagate the modified request
        response: Response = await call_next(request)

        # for every cookie in the response
        for cookie in response.headers.getlist("set-cookie"):
            # decode it
            ncookie: SimpleCookie[Any] = SimpleCookie(cookie)
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
                    value=self.encrypt(ncookie[key].value),
                    path=self.cookie_path or ncookie[key]["path"],
                    domain=self.cookie_domain or ncookie[key]["domain"],
                    secure=self.cookie_secure or ncookie[key]["secure"],
                    httponly=self.cookie_httponly or ncookie[key]["httponly"],
                    samesite=self.cookie_samesite or ncookie[key]["samesite"],
                )

        return response
