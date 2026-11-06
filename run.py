from app import create_app, db
from app.models import User, Order
from dotenv import load_dotenv
import os

# Load .env file if it exists
load_dotenv()

# Use production config if DATABASE_URL is a postgres URL,
# or if FLASK_ENV=production, or if running on Vercel
_db_url   = os.environ.get('DATABASE_URL', '')
_env      = os.environ.get('FLASK_ENV', '')
_is_prod  = (
    os.environ.get('VERCEL') or
    _env == 'production' or
    _db_url.startswith('postgres')
)
config_mode = 'production' if _is_prod else 'development'

app = create_app(config_mode)

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Order': Order}

if __name__ == '__main__':
    app.run(port=5000)
