from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwk, jwt

from app.core.config import get_settings


@dataclass(frozen=True, slots=True)
class AuthUser:
    id: UUID
    email: str | None


def _auth_user_from_payload(payload: dict) -> AuthUser:
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )
    try:
        user_id = UUID(sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid subject in token",
        ) from exc
    return AuthUser(id=user_id, email=payload.get("email"))


def _decode_with_hs256(token: str, secret: str) -> dict:
    return jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        audience="authenticated",
        options={"verify_aud": True},
    )


def _decode_with_jwks(token: str, supabase_url: str) -> dict:
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    if not kid:
        raise JWTError("Missing kid in token header")

    jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    with httpx.Client(timeout=10.0) as client:
        response = client.get(jwks_url)
        response.raise_for_status()
        jwks = response.json()

    key_data = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if not key_data:
        raise JWTError("No matching JWK for kid")

    public_key = jwk.construct(key_data)
    alg = key_data.get("alg", "RS256")
    return jwt.decode(
        token,
        public_key,
        algorithms=[alg],
        audience="authenticated",
        options={"verify_aud": True},
    )


def decode_supabase_jwt(token: str) -> AuthUser:
    settings = get_settings()

    try:
        payload = _decode_with_hs256(token, settings.supabase_jwt_secret)
        return _auth_user_from_payload(payload)
    except JWTError:
        pass

    if settings.supabase_url:
        try:
            payload = _decode_with_jwks(token, settings.supabase_url)
            return _auth_user_from_payload(payload)
        except (JWTError, httpx.HTTPError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            ) from exc

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )
