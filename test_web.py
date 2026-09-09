from aiohttp import web
from services.web_server import setup_web_server_routes
from core.tarot.loader import load_all_decks
from core.tarot.service import TarotService

tarot = TarotService(load_all_decks())
app = web.Application()
app.router.add_get("/", lambda r: web.Response(text="ok"))
setup_web_server_routes(app, tarot_service=tarot)
web.run_app(app, port=8080)
