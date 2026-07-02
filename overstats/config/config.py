from __future__ import annotations

_INJECTED_CONFIG: dict | None = None


def inject_config(cfg: dict) -> None:
    global _INJECTED_CONFIG, ANALYSIS_BASE_URL, ANALYSIS_API_KEY, ANALYSIS_PERSONA_PROMPT
    global PATCH_NOTES_USE_INTERNATIONAL_PROXY, PATCH_NOTES_INTERNATIONAL_PROXY
    _INJECTED_CONFIG = cfg
    # 动态更新 analysis 相关变量，确保运行时读到最新注入值
    analysis = cfg.get("analysis", {}) if isinstance(cfg.get("analysis"), dict) else {}
    ANALYSIS_BASE_URL = str(analysis.get("_resolved_base_url", "") or "").strip()
    ANALYSIS_API_KEY = str(analysis.get("_resolved_api_key", "") or "").strip()
    ANALYSIS_PERSONA_PROMPT = str(analysis.get("_resolved_persona_prompt", "") or "").strip()
    network = cfg.get("network", {}) if isinstance(cfg.get("network"), dict) else {}
    PATCH_NOTES_USE_INTERNATIONAL_PROXY = bool(network.get("patch_notes_use_international_proxy", False))
    PATCH_NOTES_INTERNATIONAL_PROXY = str(network.get("patch_notes_international_proxy", "") or "").strip()


def _get(key: str, default: object = None) -> object:
    if _INJECTED_CONFIG is not None:
        return _INJECTED_CONFIG.get(key, default)
    return default


API_HOST = "127.0.0.1"
API_PORT = 18080
USE_STREAM_RESPONSE = True

DASHEN_ACCOUNTS = _get("dashen_accounts", [])
DASHEN_DTS = _get("dashen_global_dashen_dts", 2026)
DASHEN_SERVER = _get("dashen_global_dashen_server", 1)
DASHEN_ACCOUNT_MAX_REQUESTS_PER_SECOND = _get("dashen_global_account_max_requests_per_second", 5)
DASHEN_ACCOUNT_RATE_LIMIT_WINDOW_SECONDS = _get("dashen_global_account_rate_limit_window_seconds", 1.0)
DASHEN_CLIENT_TYPE = "60"
DASHEN_ORIGIN = "https://act.ds.163.com"
DASHEN_REFERER = "https://act.ds.163.com/"
DASHEN_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 "
    "app/df_client dfVersion/100111"
)
DASHEN_ACCOUNT_FAILURE_COOLDOWN_SECONDS = _get("dashen_global_account_failure_cooldown_seconds", 60)
DASHEN_MAX_CONCURRENT_REQUESTS = _get("dashen_global_max_concurrent_requests", 2)

DASHEN_INTERNATIONAL_PROXY = _get("network_netease_proxy", "")
DASHEN_NETEASE_PROXIES = [None]

OW_ESPORTS_URL = ""
OW_ESPORTS_PAYLOAD = {"ids": []}

DASHEN_CURRENT_SEASON = 23
DASHEN_HISTORY_START_SEASON = 15

OW_HERO_LEADERBOARD_CN_SEASON = 3

ANALYSIS_BASE_URL = ""
ANALYSIS_API_KEY = ""
ANALYSIS_DEEPSEEK_MODEL = "deepseek-chat"

PATCH_NOTES_USE_INTERNATIONAL_PROXY = _get("network_patch_notes_use_international_proxy", False)
PATCH_NOTES_INTERNATIONAL_PROXY = _get("network_patch_notes_international_proxy", "")

ANALYSIS_PERSONA_PROMPT = ""
