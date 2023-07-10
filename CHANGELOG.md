# Changelog

All notable changes to this project will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2023-07-10

### Added

- A warning regarding possible browser rejection of insecure cookies with `SameSite=None`. See [note 3](https://caniuse.com/same-site-cookie-attribute).

### Fixed

- Existing `Set-Cookie` headers are removed from the response and replaced by their encrypted counterparts (@RealOrangeOne in #6).
- A ghost bug (one that didn't affect anything due to downstream behavior).

## [1.1.0] - 2023-04-25

### Added

- Exposed encryption, decryption, and utility functions to better support subclass customization.
- `SecureCSRFMiddleware` to the new `securecookies.extras` module to patch new and existing tooling to support secure cookies.

### Changed

- Better diagram support in documentation.
- Replaced Poetry with PDM for dependency and package management.

## [1.0.2] - 2022-05-18

### Fixed

- Support for Python 3.7.

## [1.0.1] - 2022-05-09

### Changed

- Starlette dependency from `^0.20.0` to `>=0.6.1`.

## [1.0.0] - 2022-05-08

### Added

- Starlette middleware for encrypting and decrypting cookies.
- Ability to filter cookies on which to behave.
- Ability to overwrite cookie attributes through the middleware.
- Complete documentation.
- 100% passing test coverage.
