from pydantic import BaseSettings
import os
import pathlib

root = pathlib.Path(__file__).parent.parent
env_file = root / '.env'


class Settings(BaseSettings):
    project_root: pathlib.Path = root
    secret: str = os.urandom(24).hex()
    database_uri: str = "mysql+mysqldb://gunicorn:password@127.0.0.1:3306/open_ai"
    token_url: str = "/login"
    api_key: str = "MY_API_KEY"
    api_model: str = "text-davinci-003"
    api_max_token: int = 2048
    api_temperature: float = 0.8

    class Config:
        env_file = '.env'


Config = Settings(_env_file=env_file)
