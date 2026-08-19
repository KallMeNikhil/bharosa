from app.core.config import Settings, get_settings


def test_settings_load_defaults(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    get_settings.cache_clear()
    settings = Settings(_env_file=None)
    assert settings.app_name == "bharosa-backend"
    assert settings.environment == "development"
    assert settings.api_v1_prefix == "/api/v1"


def test_settings_override_via_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()
    settings = Settings()
    assert settings.environment == "production"
    assert settings.is_production is True
    get_settings.cache_clear()
