# Changelog

All notable changes to this project will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
