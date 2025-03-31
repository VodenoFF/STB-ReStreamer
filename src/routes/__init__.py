"""
Route modules for STB-ReStreamer.
"""
from src.routes.main import main_bp
from src.routes.streaming import streaming_bp
from src.routes.hdhr import hdhr_bp
from src.routes.portals import portals_bp
from src.routes.settings import settings_bp
from src.routes.channel_groups import groups_bp

__all__ = [
    'main_bp',
    'streaming_bp',
    'hdhr_bp',
    'portals_bp',
    'settings_bp',
    'groups_bp'
] 