![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/thearchitector/starlette-securecookies/CI.yaml?label=tests&style=flat-square)
![PyPI - Downloads](https://img.shields.io/pypi/dw/starlette-securecookies?style=flat-square)
![GitHub](https://img.shields.io/github/license/thearchitector/starlette-securecookies?style=flat-square)
[![Buy a tree](https://img.shields.io/badge/Treeware-%F0%9F%8C%B3-lightgreen?style=flat-square)](https://ecologi.com/eliasgabriel?r=6128126916bfab8bd051026c)

Customizable middleware for adding automatic cookie encryption and decryption to Starlette applications.

## How it works?

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

![middleware sequence diagram](https://mermaid.ink/svg/pako:eNp9kMFqwzAQRH9FCIwOjeldh0DbpLdCIFdfhDRplsqSu1qTBON_r9q61IfSPS7vMcNM2ucAbXXTTJRIrJqMnNHDWGVOmVHEzHPTdKngfUTy2JF7Zdd3SdV75Hwp4Ha7vXuhECIujmHVPnm-DYKgfM5vhPJN_yKfwsMwRPJOKCernikKuAr3aoc_5RVe7XYdd4iOkuAq_8S1S9V1OXOEtE9filFnuAAueqN7cO8o1FGmLs31MQ7BCfaBJLO2JxcLNtqNko-35LUVHvEDLess1PwBXd56Xg)
