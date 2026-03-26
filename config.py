import os
basedir = os.path.abspath(os.path.dirname(__file__))


def get_database_url():
    url = os.environ.get('DATABASE_URL')
    if url:
        # Neon (and some other providers) give 'postgres://' but SQLAlchemy 1.4+ requires 'postgresql://'
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        return url
    # Fallback to local SQLite for development only
    return 'sqlite:///' + os.path.join(basedir, 'app.db')


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = get_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Gmail SMTP config — set these as environment variables in Vercel dashboard
    # MAIL_SERVER=smtp.gmail.com
    # MAIL_PORT=587
    # MAIL_USE_TLS=1
    # MAIL_USERNAME=your-gmail@gmail.com
    # MAIL_PASSWORD=your-gmail-app-password  (use an App Password, not your real password)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    ADMINS = [os.environ.get('ADMIN_EMAIL') or 'your-email@example.com']
    LANGUAGES = ['en', 'es']
    POSTS_PER_PAGE = 25
