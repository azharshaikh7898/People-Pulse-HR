"""One error type for business-rule failures. Services raise it, main.py turns it into JSON."""


class AppError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def not_found(what: str) -> AppError:
    return AppError(404, f"{what} not found")


def conflict(detail: str) -> AppError:
    return AppError(409, detail)


def forbidden(detail: str = "You do not have permission to do this") -> AppError:
    return AppError(403, detail)


def bad_request(detail: str) -> AppError:
    return AppError(400, detail)
