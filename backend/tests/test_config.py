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


def test_production_names_every_setting_left_at_its_development_value():
    problems = Settings(_env_file=None, environment="production").production_problems()
    assert any("SIGNING_MASTER_KEY" in problem for problem in problems)
    assert any("CLIENT_REFERENCE_SALT" in problem for problem in problems)


def test_production_with_real_secrets_has_no_problems():
    settings = Settings(
        _env_file=None,
        environment="production",
        signing_master_key="bWJtYm1ibWJtYm1ibWJtYm1ibWJtYm1ibWJtYm1ibWI=",
        client_reference_salt="a-real-salt",
    )
    assert settings.production_problems() == []


def test_development_never_reports_production_problems():
    assert Settings(_env_file=None, environment="development").production_problems() == []
