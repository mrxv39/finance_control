from api_routes.blueprint import api_bp

# Importa módulos para que se registren las rutas (decorators)
from api_routes.gastos import *       # noqa: F401,F403
from api_routes.resumen import *      # noqa: F401,F403
from api_routes.sugerencias import *  # noqa: F401,F403
