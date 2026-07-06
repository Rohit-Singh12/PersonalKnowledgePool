from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

env = Path(__file__).resolve().parent.parent / ".env"
print(env)

class Settings(BaseSettings):
	DATABASE_URL: str
	
	model_config = SettingsConfigDict(
										env_file=env,
										extra="ignore"
									)

settings = Settings() # type: ignore
