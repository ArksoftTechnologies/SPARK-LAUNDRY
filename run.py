from app import create_app, db
from app.models import User, Order # Import models for shell context

import os

# Determine config based on environment
# Vercel sets the 'VERCEL' environment variable to '1'
config_mode = 'production' if os.environ.get('VERCEL') else 'development'

app = create_app(config_mode)

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Order': Order}

if __name__ == '__main__':
    app.run(port=5000)
