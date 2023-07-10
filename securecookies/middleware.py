import sys
import warnings
from http.cookies import SimpleCookie
from typing import List, Optional

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

        if cookie_samesite:
            samesite = cookie_samesite.lower()

            if samesite not in ["strict", "lax", "none"]:
                raise BadArgumentError(
                    "SameSite attribute must be either 'strict', 'lax' or 'none'"
                )
            elif samesite == "none" and not self.cookie_secure:
                warnings.warn(
                    "Insecure cookies with a SameSite='None' attribute may be rejected"
                    " on newer browser versions (draft-ietf-httpbis-rfc6265bis). See"
                    " https://caniuse.com/same-site-cookie-attribute for compat notes."
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

    def should_process_cookie(self, cookie: str) -> bool:
        """Determines if the cookie should be included for processing."""
        return (
            (not self.included_cookies and not self.excluded_cookies)
            or (self.included_cookies is not None and cookie in self.included_cookies)
            or (
                self.excluded_cookies is not None
                and cookie not in self.excluded_cookies
            )
        )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if len(request.cookies):
            cookies: SimpleCookie[str] = SimpleCookie()
            for cookie, value in request.cookies.items():
                if self.should_process_cookie(cookie):
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

        # Extract the cookie headers to be mutated
        cookie_headers = response.headers.getlist("set-cookie")
        del response.headers["set-cookie"]

        for cookie_header in cookie_headers:
            ncookie: SimpleCookie[str] = SimpleCookie(cookie_header)
            key = next(iter(ncookie.keys()))

            if self.should_process_cookie(key):
                ncookie[key] = self.encrypt(ncookie[key].value)

                # Mutate the cookie based on middleware defaults (if provided)
                if self.cookie_path is not None:
                    ncookie[key]["path"] = self.cookie_path

                if self.cookie_domain is not None:
                    ncookie[key]["domain"] = self.cookie_domain

                if self.cookie_secure is not None:
                    ncookie[key]["secure"] = self.cookie_secure

                if self.cookie_httponly is not None:
                    ncookie[key]["httponly"] = self.cookie_httponly

                if self.cookie_samesite is not None:
                    ncookie[key]["samesite"] = self.cookie_samesite

            response.headers.append(
                "set-cookie", ncookie.output(header="", sep=";").strip()
            )

        return response
