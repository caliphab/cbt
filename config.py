import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')

    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_name = os.getenv('DB_NAME')
    SQLALCHEMY_DATABASE_URI = f"mysql://{db_user}:{db_password}@{db_host}/{db_name}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    EXAM_AUTO_SUBMIT_WARNING_MINUTES = 5

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}