from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    DATABASE_URL: str
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    KEYCLOAK_URL: str = ""
    KEYCLOAK_REALM: str = "master"
    
    KEYCLOAK_CLIENT_ID: str = "smartlock-api"
    KEYCLOAK_CLIENT_SECRET: str 
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=False
    )

settings = Settings()