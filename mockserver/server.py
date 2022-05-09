import logging

from sanic import Sanic

import cfg4py
from mockserver.handlers import global_accunt_info
from mockserver.route_map import initialize_blueprint

logger = logging.getLogger(__name__)


app = Sanic("trade-mock-adaptor")


def server_start() -> int:
    # load information from config file
    server_config = cfg4py.get_instance()

    server_info = server_config.server_info
    account_id = server_info.account_id
    account_capital = server_info.account_captital
    global_accunt_info["info"] = {
        "account": account_id,
        "available": account_capital,
        "pnl": 0,
        "total": account_capital,
        "ppnl": 0,
    }

    initialize_blueprint(app)

    port = server_info.port
    logger.info("server initialized at port: %d", port)
    app.run(host="0.0.0.0", port=port)
