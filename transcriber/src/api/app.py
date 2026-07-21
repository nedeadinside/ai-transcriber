from config import load_config
from core.api.app import create_app

from .routes import router

app = create_app(load_config(), router)
