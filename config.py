import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-gab-lab-finance'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///gab_lab_finance.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False