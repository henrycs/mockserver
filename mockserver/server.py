import logging

import cfg4py
from sanic import Sanic

from mockserver.handlers import global_accunt_info
from mockserver.route_map import initialize_blueprint

logger = logging.getLogger(__name__)


app = Sanic("trader-gm-mock-adaptor")


def server_start() -> int:
    # load information from config file
    server_config = cfg4py.get_instance()

    # access_token : "ec31c154fc0cbf4ba39eb48689ebcbfaacf8067f"
    # case_folder: /home/henry/share/testcases
    # account_id: "145be423-a021-11ec-8e33-00163e0a4100"
    # account_captital: 1000000

    """
    {
        "account": "145be423-a021-11ec-8e33-00163e0a4100",
        "available": 973314.341,
        "pnl": 0,
        "total": 1000000,
        "ppnl": 0
    }
    """
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
