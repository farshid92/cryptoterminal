from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    symbol: str = 'BTCUSDT'
    timeframes: str = '1m,5m,15m,1h,4h,1d'
    seed: int = 42
    database_url: str = 'postgresql+asyncpg://postgres:postgres@localhost:5432/ct'
    valkey_url: str = 'valkey://localhost:6379'
    minio_endpoint: str = 'localhost:9000'
    minio_user: str = 'ct'
    minio_pass: str = 'changeme'
    mlflow_tracking_uri: str = 'http://localhost:5000'
    news_source: str = 'cryptocompare'
    budget_max_trials_optuna: int = 200


settings = Settings()
