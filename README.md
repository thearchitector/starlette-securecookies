# starlette-securecookies

![GitHub Workflow Status](https://img.shields.io/github/workflow/status/thearchitector/starlette-securecookies/CI?label=tests&style=flat-square)
![PyPI - Downloads](https://img.shields.io/pypi/dw/starlette-securecookies?style=flat-square)
![GitHub](https://img.shields.io/github/license/thearchitector/starlette-securecookies?style=flat-square)
[![Buy a tree](https://img.shields.io/badge/Treeware-%F0%9F%8C%B3-lightgreen?style=flat-square)](https://ecologi.com/eliasgabriel?r=6128126916bfab8bd051026c)

Customizable middleware for adding automatic cookie encryption and decryption to Starlette applications.

Tested support on Python 3.7, 3.8, 3.9, and 3.10 on macOS, Windows, and Linux.

## How it works?

```mermaid
sequenceDiagram
    Browser->>+Middleware: Encrypted cookies
    Middleware->>+Application: Filtered / Decrypted cookies
    Application->>-Middleware: Plaintext cookies
    Middleware->>-Browser: Encrypted 'Set-Cookie' headers
```

For any incoming cookies:

1. Requests sent from the client's browser to your application are intercepted by `SecureCookiesMiddleware`.
2. All `Cookie` headers are parsed and filter. Only cookies in the `included_cookies` and `excluded_cookies` parameters are parsed. All cookies are included by default.
3. The cookies are decrypted. If cookie cannot be decrypted, or is otherwise invalid, it is discarded by default (`discard_invalid=True`).
4. Any included and valid encrypted cookies in the ASGI request scope are replaced by the decrypted ones.
5. The request scope is passed to any future middleware, and eventually your application. Cookies can be read normally anywhere downstream.

For any outgoing cookies:

7. Your application sets cookies with `response.set_cookie` as usual.
8. All responses returned by your application are intercepted by `SecureCookiesMiddleware`.
9. Cookies in the `included_cookies` and `excluded_cookies` parameters are re-encrypted, and their attributes (like `"SameSite"` and `"HttpOnly"`) are overridden by the parameters set in `SecureCookiesMiddleware`.
10. The cookies in the response are replaced by the re-encrypted cookies, and the response is propagated to Starlette to return to the client's browser.

## Installation

```sh
$ poetry add starlette-securecookies
# or
$ python -m pip install --user starlette-securecookies
```

## Usage

This is a Starlette-based middleware, so it can be used in any Starlette application or Starlette-based application (like [FastAPI](https://fastapi.tiangolo.com/advanced/middleware/) or [Starlite](https://starlite-api.github.io/starlite/usage/7-middleware/)).

For example,

```python
from starlette.applications import Starlette
from starlette.middleware import Middleware

from securecookies import SecureCookiesMiddleware

middleware = [
    Middleware(
        SecureCookiesMiddleware, secrets=["SUPER SECRET SECRET"]
    )
]

app = Starlette(routes=..., middleware=middleware)
```

## License

This software is licensed under the [BSD 3-Clause License](LICENSE).

This package is Treeware. If you use it in production, consider buying the world a tree to thank me for my work. By contributing to my forest, you’ll be creating employment for local families and restoring wildlife habitats.
