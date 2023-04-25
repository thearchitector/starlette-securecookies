"""
# securecookies.extras

starlette-securecookies also ships with some common middleware and tools modified and
extended to work with secure cookies.

- **`csrf.SecureCSRFMiddleware`**: Adds compatibility to the CSRF middleware provided
by [starlette_csrf](https://github.com/frankie567/starlette-csrf). To use it, simply
add it to your list of middleware (keep in mind the ordering). If you don't want to
specify `starlette_csrf` as a direct dependency, you can also install it through the
`[csrf]` package extra.
"""

__all__ = []  # type: ignore
