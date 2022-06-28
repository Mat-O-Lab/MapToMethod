import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "hard to guess string"
    TEMPORAL_FOLDER = os.environ.get("TEMPORAL_FOLDER") or "tmp"
    TEMPLATES_AUTORELOAD = True
    SWAGGER_URL = "/api/docs"
    API_URL = "/static/swagger.json"

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}
