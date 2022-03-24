import logging
import urllib.parse

from sanic import Blueprint, Sanic, request, response

import mockserver.handlers as handler
from mockserver.handlers import global_accunt_info
from mockserver.trade import BidType, OrderSide
from mockserver.utils import check_request_token, make_response

logger = logging.getLogger(__name__)

bp_mockserver = Blueprint("mock-trade-server", strict_slashes=False)
bp_mockcontroller = Blueprint(
    "mock-server-controller", url_prefix="/mock", strict_slashes=False
)


# -------------- mock server controller  ---------------
@bp_mockcontroller.route("/load/<case>", methods=["GET"])
async def bp_mock_load(request, case: str):
    if case is None:
        return response.json(make_response(404, "No case file specified"))

    case_name = urllib.parse.unquote(case)
    result = handler.wrapper_read_case_file(case_name)

    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    return response.json(make_response(0, "OK", result["data"]))


@bp_mockcontroller.route("/load", methods=["POST"])
async def bp_mock_load2(request):
    case_name = request.json.get("case")
    result = handler.wrapper_read_case_file(case_name)

    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    return response.json(make_response(0, "OK", result["data"]))


# 如果是委托更新指令，直接执行，然后进到下一步
@bp_mockcontroller.route("/proceed")
async def bp_mock_proceed(request):
    result = handler.wrapper_proceed_non_trade_action()
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    return response.json(make_response(0, "OK", result["data"]))


@bp_mockcontroller.route("/current")
async def bp_mock_current(request):
    result = handler.wrapper_exec_current()

    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    return response.json(make_response(0, "OK", result["data"]))


@bp_mockcontroller.route("/history")
async def bp_mock_history(request):
    result = handler.wrapper_exec_history()
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    return response.json(make_response(0, "OK", result["data"]))


@bp_mockcontroller.route("/reset")
async def bp_mock_reset_mockdata(request):
    handler.wrapper_reset_exec_data()
    return response.json(make_response(0, "OK", {"data": "all data cleared"}))


@bp_mockcontroller.route("/")
async def bp_mockserver_default_route(request):
    return response.text("load, proceed, current, history, reset")


# ------------------ mock trade server ------------------------


def check_trade_server_account(account_id: str):
    acct_info = global_accunt_info["info"]
    if account_id in acct_info["account"]:
        return True
    else:
        return False


@bp_mockserver.middleware("request")
async def validate_request(request: request):

    is_authenticated = check_request_token(request.headers.get("Authorization"))
    if not is_authenticated:
        return response.json(make_response(401, "invalid access token"), 401)

    account = request.headers.get("Account-ID")
    if account is None or (not check_trade_server_account(account)):
        return response.json(make_response(401, "invalid account id"), 401)


@bp_mockserver.route("/balance", methods=["GET"])
async def bp_mock_get_balance(request):
    account_id = request.headers.get("Account-ID")

    result = handler.wrapper_get_balance(account_id)
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    return response.json(make_response(0, "OK", result["data"]))


@bp_mockserver.route("/positions", methods=["GET"])
async def bp_mock_get_positions(request):
    account_id = request.headers.get("Account-ID")

    result = handler.wrapper_get_positions(account_id)
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    return response.json(make_response(0, "OK", result["data"]))


@bp_mockserver.route("/buy", methods=["POST"])
async def bp_mock_buy(request):
    account_id = request.headers.get("Account-ID")
    symbol = request.json.get("security")
    price = request.json.get("price")
    volume = request.json.get("volume")
    logger.info(f"buy: code: {symbol}, price: {price}, volume: {volume}")

    result = handler.wrapper_trade_operation(
        account_id, symbol, price, volume, OrderSide.BUY, BidType.LIMIT
    )
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    # we can check result.status if this entrust success
    logger.info(f"buy result: {result['data']}")
    return response.json(make_response(0, "OK", result["data"]))


@bp_mockserver.route("/market_buy", methods=["POST"])
async def bp_mock_market_buy(request):
    account_id = request.headers.get("Account-ID")
    symbol = request.json.get("security")
    price = request.json.get("price")
    volume = request.json.get("volume")
    logger.info(f"buy: code: {symbol}, price: {price}, volume: {volume}")

    result = handler.wrapper_trade_operation(
        account_id, symbol, price, volume, OrderSide.BUY, BidType.MARKET
    )
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    # we can check result.status if this entrust success
    logger.info(f"buy result: {result['data']}")
    return response.json(make_response(0, "OK", result["data"]))


@bp_mockserver.route("/sell", methods=["POST"])
async def bp_mock_sell(request):
    account_id = request.headers.get("Account-ID")
    symbol = request.json.get("security")
    price = request.json.get("price")
    volume = request.json.get("volume")
    logger.info(f"buy: code: {symbol}, price: {price}, volume: {volume}")

    result = handler.wrapper_trade_operation(
        account_id, symbol, price, volume, OrderSide.SELL, BidType.LIMIT
    )
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    # we can check result.status if this entrust success
    logger.info(f"buy result: {result['data']}")
    return response.json(make_response(0, "OK", result["data"]))


@bp_mockserver.route("/market_sell", methods=["POST"])
async def bp_mock_market_sell(request):
    account_id = request.headers.get("Account-ID")
    symbol = request.json.get("security")
    price = request.json.get("price")
    volume = request.json.get("volume")
    logger.info(f"buy: code: {symbol}, price: {price}, volume: {volume}")

    result = handler.wrapper_trade_operation(
        account_id, symbol, price, volume, OrderSide.SELL, BidType.MARKET
    )
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    # we can check result.status if this entrust success
    logger.info(f"buy result: {result['data']}")
    return response.json(make_response(0, "OK", result["data"]))


@bp_mockserver.route("/cancel_entrust", methods=["POST"])
async def bp_mock_cancel_entrust(request):
    account_id = request.headers.get("Account-ID")

    entrust_no = request.json.get("entrust_no")
    logger.info("cancel entrusts: %s -> %s", account_id, entrust_no)
    if isinstance(entrust_no, list):
        return response.json(
            make_response(
                -1, "cancel_entrust: only 1 entrust_no acceptable, no list permitted"
            )
        )

    result = handler.wrapper_cancel_entrust(account_id, entrust_no)
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    # we can check result.status if this entrust success
    logger.info(f"cancel result: {result['data']}")
    return response.json(make_response(0, "OK", result["data"]))


@bp_mockserver.route("/cancel_entrusts", methods=["POST"])
async def bp_mock_cancel_entrusts(request):
    account_id = request.headers.get("Account-ID")

    order_list = request.json.get("entrust_no")
    logger.info("cancel entrusts: %s -> %s", account_id, order_list)
    if not isinstance(order_list, list):
        return response.json(
            make_response(-1, "cancel_entrusts: entrust_no must be list")
        )

    result = handler.wrapper_cancel_entrusts(account_id, order_list)
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    # we can check result.status if this entrust success
    logger.info(f"cancel result: {result['data']}")
    return response.json(make_response(0, "OK", result["data"]))


@bp_mockserver.route("/today_entrusts", methods=["POST"])
async def bp_mock_get_today_all_entrusts(request):
    account_id = request.headers.get("Account-ID")

    order_list = request.json.get("entrust_no")
    logger.info("today_entrusts: %s -> %s", account_id, order_list)

    result = handler.wrapper_get_today_entrusts(order_list)
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    return response.json(make_response(0, "OK", result["data"]))


# 当前z trade server不用这个接口
@bp_mockserver.route("/today_trades", methods=["POST"])
async def bp_mock_get_today_all_trades(request):
    account_id = request.headers.get("Account-ID")
    print(account_id)

    result = handler.wrapper_get_today_trades()
    if result["status"] != 200:
        return response.json(make_response(-1, result["msg"]))

    return response.json(make_response(0, "OK", result["data"]))


def initialize_blueprint(app: Sanic):
    """initialize sanic server blueprint

    Args:
        app (Sanic): instance of this sanic server
    """

    app.blueprint(bp_mockcontroller)
    app.blueprint(bp_mockserver)

    logger.info("blueprint v1 added into app object")
