# Sprint 1 Authentication

## Purpose

This note documents the implemented Sprint 1 authentication foundation for the
backend application.

## Implemented Scope

- User registration with Argon2id password hashing.
- Login with email and password.
- JWT access and refresh token generation.
- Refresh-token exchange for a new access token.
- Current-user endpoint at `GET /api/v1/users/me`.
- Authentication middleware for protected `/api/v1` paths.
- Standard error envelopes for authentication failures.

## Public Paths

The following paths do not require an access token:

- `GET /health`
- `GET /api/v1/health`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`

All other `/api/v1` paths require:

```http
Authorization: Bearer <access_token>
```

## Token Behavior

- Access tokens use JWT token type `access`.
- Refresh tokens use JWT token type `refresh`.
- Access token lifetime follows ADR-009 and the current JWT service constant:
  15 minutes.
- Refresh token lifetime is 30 days.
- Refresh-token exchange validates the refresh token, loads the current user,
  rejects disabled or soft-deleted users, and issues the new access token from
  the current database user record.

## Current User Context

Protected API requests are authenticated before route handling. The middleware:

- extracts the Bearer token,
- validates signature, expiration, and token type,
- loads the user,
- rejects missing, disabled, or soft-deleted users,
- attaches the user to `request.state.current_user`.

Route handlers should continue to use:

```python
Depends(get_current_user)
```

This keeps ownership validation explicit at the API/service boundary.

## Error Codes

Authentication failures return the standard error envelope with:

- `INVALID_TOKEN`
- `TOKEN_EXPIRED`
- `INVALID_CREDENTIALS`
- `ACCOUNT_DISABLED`

Token values, passwords, stack traces, and internal details are not returned to
API clients.

## Test Commands

Run the authentication-focused suite:

```powershell
uv run pytest tests\test_auth_middleware.py tests\test_auth_login_endpoint.py tests\test_auth_refresh_endpoint.py tests\test_current_user_endpoint.py tests\test_jwt.py tests\test_refresh_token.py tests\test_security.py
```

Run the full backend suite:

```powershell
uv run pytest
```
