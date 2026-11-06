import os
from app import create_app

app_env = os.environ.get("APP_ENV", os.environ.get("FLASK_ENV", "production"))
app = create_app(app_env)

if __name__ == "__main__":
    app.run()
