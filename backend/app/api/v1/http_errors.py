from fastapi import HTTPException, status


def not_found(detail: str = "Not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def from_value_error(exc: ValueError) -> HTTPException:
    return not_found(str(exc))
