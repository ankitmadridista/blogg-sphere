import logging
from logging.handlers import RotatingFileHandler
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from config import Config
from flask_moment import Moment
from flask_babel import Babel
from flask import request

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'
login.login_message_category = 'warning'
mail = Mail(app)
moment = Moment(app)
babel = Babel(app)

if not app.debug:
    # File-based logging is disabled on Vercel (read-only filesystem).
    # Logs are available via the Vercel dashboard instead.
    if not os.environ.get('VERCEL'):
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/blogApp.log', maxBytes=10240,
                                           backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('blogApp startup')


@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(app.config['LANGUAGES'])


from app import routes, models, errors
from app.utils import render_markdown
app.jinja_env.filters['markdown'] = render_markdown

from flask_wtf.csrf import generate_csrf
app.jinja_env.globals['csrf_token'] = generate_csrf