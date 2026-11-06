import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app import create_app
from app.extensions import db
import app.models  # Ensure all 55 models are loaded

app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
