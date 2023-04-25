try:
    from starlette_csrf.middleware import CSRFMiddleware
except ImportError:
    raise AssertionError("starlette_csrf must be installed to use the CSRF extra.")

from typing import Optional

from starlette.requests import Request

from ..middleware import SecureCookiesMiddleware


class SecureCSRFMiddleware(CSRFMiddleware):
    async def _get_submitted_csrf_token(self, request: Request) -> Optional[str]:
        """
        We're using encrypted cookies, so the contents of the header coming from the
        client will also be encrypted. The incoming cookie is decrypted automatically
        but the header is not, so we need to decrypt it manually so CSRF middleware
        can compare them correctly.
        """
        # middleware is built and instantiated once during application creation.
        # since we don't want to recreate the middleware (seems not nice), we need to
        # loop through the entire ASGI stack to find our SecureCookieMiddleware.
        # this might be excessive but ¯\_(ツ)_/¯
        if not hasattr(self, "_secure_middleware"):
            app = request.scope["app"].middleware_stack
            while not isinstance(app, SecureCookiesMiddleware):
                try:
                    app = app.app
                except AttributeError:
                    raise Exception(
                        "You must use SecureCSRFMiddleware in conjunction with"
                        " SecureCookiesMiddleware."
                    )

            self._secure_middleware = app

        return self._secure_middleware.decrypt(request.headers[self.header_name])
