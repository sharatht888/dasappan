import os

class Config:
    # Secret key for sessions and cookies
    SECRET_KEY = os.environ.get('harambe')

    # Local MySQL Database URI (localhost with root as username and password)
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:root@localhost/interview_system'
    SQLALCHEMY_TRACK_MODIFICATIONS = False