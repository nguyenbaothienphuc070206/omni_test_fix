import os

class Config:
    DATABASE_URL = os.getenv('DATABASE_URL')
    JWT_SECRET = os.getenv('JWT_SECRET')
    PORT = os.getenv('PORT', '8000')

    @staticmethod
    def validate():
        if not Config.DATABASE_URL:
            raise ValueError('DATABASE_URL is required')
        if not Config.JWT_SECRET:
            raise ValueError('JWT_SECRET is required')

Config.validate()