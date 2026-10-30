from karenos.config import Settings


def test_settings_use_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("KAREN_AI_API_KEY", "example-key")
    monkeypatch.setenv("KAREN_AI_MODEL", "example-model")
    monkeypatch.setenv("KAREN_DATA_DIR", str(tmp_path))
    settings = Settings.from_env()

    assert settings.ai_api_key == "example-key"
    assert settings.ai_model == "example-model"
    assert settings.data_dir == tmp_path
