import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from shared import SessionMiddleware, init_db, get_session_secret
from shared.limiter import limiter
from shared.database import get_motor_client
from shared.redis import get_redis_client
from shared.webpage import webpage


def _collect_document_models():
    from core.users.models import User
    from core.classes.models import Class, ClassMembership, JoinRequest
    from tasks.templates.models import TaskTemplate, TaskAssignment, TaskScheduleRule
    from tasks.submissions.models import TaskSubmission
    from tasks.checkin.models import CheckinConfig, DailyCheckinOverride, CheckinRecord, AttendanceCorrection
    from gamification.points.models import PointTransaction, ClassPointConfig
    from gamification.badges.models import BadgeDefinition, BadgeAward
    from gamification.triggers.models import TriggerRule
    from community.feed.models import FeedPost, Reaction
    from gamification.prizes.models import Prize
    from core.system.models import SystemConfig
    return [
        User, Class, ClassMembership, JoinRequest,
        TaskTemplate, TaskAssignment, TaskScheduleRule, TaskSubmission,
        CheckinConfig, DailyCheckinOverride, CheckinRecord, AttendanceCorrection,
        PointTransaction, ClassPointConfig,
        BadgeDefinition, BadgeAward, TriggerRule,
        FeedPost, Reaction,
        Prize,
        SystemConfig,
    ]


def _register_extensions():
    from extensions.registry import registry
    from extensions.protocols.auth import AuthProvider
    from extensions.protocols.reward import RewardProvider
    from core.auth.local_provider import LocalAuthProvider
    from gamification.points.providers import CheckinRewardProvider, SubmissionRewardProvider

    registry.register(AuthProvider, "local", LocalAuthProvider())
    registry.register(RewardProvider, "checkin", CheckinRewardProvider())
    registry.register(RewardProvider, "submission", SubmissionRewardProvider())


@asynccontextmanager
async def lifespan(app: FastAPI):
    from core.auth.jwt import check_secret_safety
    from core.system.startup import init_redis_state, check_setup_state

    # JWT secret safety check — raises RuntimeError in production with default secret
    check_secret_safety()

    # MongoDB
    client = get_motor_client()
    db_name = os.getenv("MONGO_DB_NAME", "dts2")
    database = client[db_name]
    document_models = _collect_document_models()
    await init_db(database=database, document_models=document_models)

    # Redis — store client in app.state.redis
    redis_client = get_redis_client()
    await init_redis_state(app.state, redis_client)

    # Setup state check
    await check_setup_state(app.state)

    _register_extensions()

    # Inject site_name into WebPage global context
    config = getattr(app.state, "system_config", None)
    site_name = config.site_name if config is not None else "每日任務系統"
    webpage.webpage_context_update({"site_name": site_name})

    yield

    await app.state.redis.aclose()
    client.close()


app = FastAPI(lifespan=lifespan)

# Rate limiter — shared instance used by @limiter.limit decorators
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from shared.csrf import CSRFMiddleware

# 透過共用 resolver 取得密鑰，使 SessionMiddleware 與 JWT 簽章共用同一把密鑰。
SESSION_SECRET = get_session_secret()
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.add_middleware(CSRFMiddleware)


from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse as _RedirectResponse


class SetupGuardMiddleware(BaseHTTPMiddleware):
    """Redirect every request to /setup when the system has not been configured yet."""

    # 設定完成前需放行的路徑前綴：/setup 本身，以及靜態資源
    # （否則 CSS/JS/圖片/WASM 也會被導去 /setup，導致 setup 頁面失去樣式）
    _ALLOWED_PREFIXES = ("/setup", "/static")

    async def dispatch(self, request, call_next):
        if getattr(request.app.state, "system_config", None) is None:
            if not request.url.path.startswith(self._ALLOWED_PREFIXES):
                return _RedirectResponse(url="/setup", status_code=302)
        return await call_next(request)


app.add_middleware(SetupGuardMiddleware)

# --- Routers ---
from core.system.router import router as system_router
from core.auth.router import router as auth_router
from core.users.router import router as users_router
from core.classes.router import router as classes_router
from tasks.templates.router import router as templates_router
from tasks.submissions.router import router as submissions_router
from tasks.checkin.router import router as checkin_router
from gamification.points.router import router as points_router
from gamification.badges.router import router as badges_router
from gamification.triggers.router import router as triggers_router
from community.feed.router import router as feed_router
from gamification.prizes.router import router as prizes_router
from gamification.leaderboard.router import router as leaderboard_router
from pages.router import router as pages_router

# --- Static files (DSL WASM engine) ---
from pathlib import Path as _Path
from fastapi.staticfiles import StaticFiles as _StaticFiles

_dsl_pkg = _Path(__file__).resolve().parent.parent / "crates" / "dsl-engine" / "pkg"
if _dsl_pkg.is_dir():
    app.mount("/static/dsl-engine", _StaticFiles(directory=str(_dsl_pkg)), name="dsl-engine-static")

_static_dir = _Path(__file__).resolve().parent / "static"
if _static_dir.is_dir():
    app.mount("/static", _StaticFiles(directory=str(_static_dir)), name="static")

app.include_router(system_router)
app.include_router(auth_router)
app.include_router(pages_router)
app.include_router(users_router)
app.include_router(classes_router)
app.include_router(templates_router)
app.include_router(submissions_router)
app.include_router(checkin_router)
app.include_router(points_router)
app.include_router(badges_router)
app.include_router(triggers_router)
app.include_router(feed_router)
app.include_router(prizes_router)
app.include_router(leaderboard_router)


from fastapi import Cookie, Request
from fastapi.responses import RedirectResponse


@app.get("/")
async def root(request: Request, access_token: str | None = Cookie(default=None)):
    if access_token:
        from core.auth.jwt import decode_access_token
        try:
            decode_access_token(access_token)
            return RedirectResponse(url=request.url_for("dashboard_page"), status_code=302)
        except Exception:
            pass
    return RedirectResponse(url=request.url_for("login_page"), status_code=302)
