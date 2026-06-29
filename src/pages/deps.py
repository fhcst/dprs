"""Page-aware auth dependency — redirects to login instead of raising 401."""
from fastapi import Cookie, HTTPException, Request, status

from core.auth.jwt import decode_access_token
from core.users.models import User


def _redirect_to_login(request: Request) -> None:
    """Raise a 302 redirect to the login page, preserving the current page as `next`.

    `next` is captured ONLY for idempotent (GET) requests, and is stored as a
    same-origin RELATIVE path (request path, plus the original query string when
    present) — never the absolute request URL. This keeps the stored value in the
    single-slash relative-path format the login endpoint's `next` validator accepts,
    so deep links round-trip back to the user after login.

    Non-GET requests (e.g. an unauthenticated/expired-session POST to a protected
    endpoint like ``POST /pages/settings/password``) deliberately omit `next`. The
    post-login redirect always replays `next` as a *GET*; storing a POST-only route
    would surface a ``405 Method Not Allowed`` instead. Omitting it lets login fall
    back to ``/pages/dashboard``, matching the prior graceful behaviour.
    """
    login_url = request.url_for("login_page")
    if request.method == "GET":
        relative_next = request.url.path
        if request.url.query:
            relative_next = f"{relative_next}?{request.url.query}"
        login_url = login_url.include_query_params(next=relative_next)
    raise HTTPException(
        status_code=status.HTTP_302_FOUND,
        headers={"Location": str(login_url)},
    )


async def get_page_user(
    request: Request,
    access_token: str | None = Cookie(default=None),
) -> User:
    """
    Dependency that returns the authenticated User.

    Unlike ``get_current_user``, this redirects to the login page (302) instead
    of raising 401, so unauthenticated browser requests land on the login form.
    """
    if not access_token:
        _redirect_to_login(request)

    try:
        payload = decode_access_token(access_token)
    except Exception:
        _redirect_to_login(request)

    user_id = payload.get("user_id")
    user = await User.get(user_id)
    if user is None or not user.is_active:
        _redirect_to_login(request)

    return user
