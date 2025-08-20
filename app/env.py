from dataclasses import dataclass
from environs import Env

@dataclass
class DatabaseConfig:
    database_url: str
    
@dataclass
class RedisConfig:
    redis_url: str
    
@dataclass
class OpenAIConfig:
    openai_api_key: str

@dataclass
class Config:
    vdb: DatabaseConfig
    redis: RedisConfig
    api_key: OpenAIConfig
    secret_key: str
    debug: bool

def load_config(path: str = None) -> Config:
    env = Env()
    env.read_env(path)

    return Config(
        vdb=DatabaseConfig(database_url=env("VDB_CONN")),
        redis=RedisConfig(redis_url=env("REDIS_CONN")),
        api_key=OpenAIConfig(openai_api_key=env("OPENAI_KEY")),
        secret_key=env("SECRET_KEY"),
        debug=env.bool("DEBUG", default=False)
    )