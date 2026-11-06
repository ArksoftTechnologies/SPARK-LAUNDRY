import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # ── Security ────────────────────────────────────────────────────────────
    SECRET_KEY      = os.environ.get('SECRET_KEY') or 'change-me-in-production'
    JWT_SECRET_KEY  = os.environ.get('JWT_SECRET_KEY') or 'change-jwt-in-production'

    # ── Database ─────────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI    = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS  = {
        'pool_pre_ping': True,      # detect stale connections
        'pool_recycle':  280,       # recycle before Heroku/Render 300s timeout
    }

    # ── Email ────────────────────────────────────────────────────────────────
    MAIL_SERVER   = os.environ.get('MAIL_SERVER',   'arksofttechnologies.com')
    MAIL_PORT     = int(os.environ.get('MAIL_PORT', 465))
    MAIL_USE_TLS  = os.environ.get('MAIL_USE_TLS',  'false').lower() == 'true'
    MAIL_USE_SSL  = os.environ.get('MAIL_USE_SSL',  'true').lower()  == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'info@arksofttechnologies.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_SUBJECT_PREFIX = '[Spark Laundry]'

    # ── Brand ────────────────────────────────────────────────────────────────
    BRAND_PRIMARY   = '#0066CC'
    BRAND_SECONDARY = '#FFCC00'
    BRAND_PHONE     = '+234 915 740 6159'


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.getcwd()), 'laundry_dev.db')


class ProductionConfig(Config):
    DEBUG = False
    PROPAGATE_EXCEPTIONS = True

    @classmethod
    def init_app(cls, app):
        Config.init_app(app) if hasattr(Config, 'init_app') else None

        # Log to stderr on Render/Heroku
        import logging
        from logging import StreamHandler
        handler = StreamHandler()
        handler.setLevel(logging.WARNING)
        app.logger.addHandler(handler)

    # ── PostgreSQL — fix Heroku/Render postgres:// → postgresql:// ──────────
    _db_url = os.environ.get('DATABASE_URL', '')
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url or ('sqlite:///' + os.path.join(basedir, 'app.db'))


config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}
