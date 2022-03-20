import json
import logging
import math
from os import path

import cfg4py

from mockserver.trade import BidType, OrderSide

logger = logging.getLogger(__name__)


global_accunt_info = {"info": {}, "posistions": {}, "entursts": {}, "trades": {}}
global_case_data = {"case": "", "items": [], "index": -1, "executed": 0}
global_case_exec_list = []


def wrapper_reset_exec_data():
    # 清除所有执行记录
    global global_case_exec_list, global_case_data, global_accunt_info

    global_accunt_info["entursts"] = {}
    global_accunt_info["posistions"] = {}
    global_accunt_info["trades"] = {}

    global_case_data["case"] = ""
    global_case_data["items"] = []
    global_case_data["index"] = -1
    global_case_data["executed"] = 0

    global_case_exec_list = []


def wrapper_exec_current():
    # 读取当前正在执行的用例步骤
    casename = global_case_data["case"]
    index = global_case_data["index"]
    if index == -1:
        return {"status": 400, "msg": "no test case loaded"}

    exec_flag = global_case_data["executed"]
    items = global_case_data["items"]
    item = items[index]

    return {
        "status": 200,
        "msg": "success",
        "data": {
            "case": casename,
            "stage": item["stage"],
            "action": item["test_action"],
            "executed": exec_flag,
        },
    }


def wrapper_exec_history():
    return {"status": 200, "msg": "success", "data": global_case_exec_list}


def execute_entrust_case(item):
    data = None

    # 读取委托更新的内容
    if "entrust_update" in item:
        data = item["entrust_update"]
    if "trade_result" in item:
        data = item["trade_result"]
    if data is None:
        return None

    entrust_id = data["entrust_no"]
    entrusts = global_accunt_info["entursts"]
    entrusts[entrust_id] = data

    # 如果委托是部分成交或者全部成交，更新成交清单
    if data["status"] == 2 or data["status"] == 3:
        trades = global_accunt_info["trades"]
        trades[entrust_id] = data

    # 更新持仓信息
    # 因为持仓涉及到可平仓计算，需要历史数据支撑，暂不支持

    # 更新执行信息
    global_case_data["executed"] = 1
    global_case_exec_list.append(
        {
            "case": global_case_data["case"],
            "stage": item["stage"],
            "action": item["test_action"],
        }
    )

    return 0


def wrapper_read_case_file(casename: str):
    # 加载测试用例，检查所有步骤
    server_config = cfg4py.get_instance()
    case_dir = server_config.server_info.case_folder

    case_file = path.normpath(path.join(case_dir, f"{casename}.txt"))
    if not path.exists(case_file):
        logger.error("case file not found: %s", case_file)
        return {"status": 400, "msg": "case file not found"}

    # 测试步骤
    items = []
    try:
        with open(case_file, "r", encoding="utf-8") as reader:
            content = reader.read()
            items = json.loads(content)
    except Exception as e:
        logger.error(e)
        return {"status": 400, "msg": str(e)}

    if len(items) == 0:
        logger.error("no content found in case file")
        return {"status": 400, "msg": "no content in case file"}

    for item in items:
        print(f"item in case file:\n{item}")

    try:
        # 如果上一个测试用例还没执行完，暂不允许加载新的
        old_case = global_case_data["case"]
        if old_case == casename:
            return {"status": 400, "msg": f"cannot load same test case: {old_case}"}

        old_items = global_case_data["items"]
        old_index = global_case_data["index"]
        old_exec_flag = global_case_data["executed"]
        if old_index != -1 and old_exec_flag == 0:
            old_item = old_items[old_index]
            return {
                "status": 400,
                "msg": f"actions in last case not executed: {old_case}:{old_item['stage']}",
            }

        # 加载新的用例
        global_case_data["case"] = casename
        global_case_data["items"] = items
        # 准备执行第一个用例
        global_case_data["index"] = 0
        global_case_data["executed"] = 0

        item = items[0]
        if item["test_action"] == "entrust_update":
            execute_entrust_case(item)
            act_result = "action executed"

        return {
            "status": 200,
            "msg": "OK",
            "data": {
                "case": casename,
                "stage": item["stage"],
                "action": item["test_action"],
                "status": "to be executed",
            },
        }
    except Exception as e:
        logger.error(e)
        return {"status": 500, "msg": e.msg}


def wrapper_proceed_nextstep():
    # 执行下一个测试步骤，如果是委托更新，则立刻执行
    casename = global_case_data["case"]
    items = global_case_data["items"]
    last_index = global_case_data["index"]

    # 尚未加载用例
    if len(casename) == 0 or last_index == -1:
        return {"status": 400, "msg": f"no case file loaded, {casename}"}

    # 最后一个步骤已经执行了
    if last_index == len(items) - 1:
        item = items[last_index]
        last_stage = item["stage"]
        return {
            "status": 400,
            "msg": f"no more stages, last stage: {casename}:{last_stage}",
        }

    # 如果上一个步骤未执行
    exec_flag = global_case_data["executed"]
    if exec_flag == 0:
        item = items[last_index]
        last_stage = item["stage"]
        action = item["test_action"]
        return {
            "status": 400,
            "msg": f"current action not executed: {casename}->{last_stage}: {action}",
        }

    # 获取下一个步骤
    item = items[last_index + 1]
    global_case_data["index"] = last_index + 1
    global_case_data["executed"] = 0

    if item["test_action"] == "entrust_update":
        execute_entrust_case(item)
        return {
            "status": 200,
            "msg": "OK",
            "data": {
                "case": casename,
                "stage": item["stage"],
                "action": item["test_action"],
                "status": "action executed",
            },
        }

    return {
        "status": 200,
        "msg": "OK",
        "data": {
            "case": casename,
            "stage": item["stage"],
            "action": item["test_action"],
            "status": "to be executed",
        },
    }


def wrapper_get_balance(account_id: str):
    acct_info = global_accunt_info["info"]
    return {"status": 200, "msg": "success", "data": acct_info}


def wrapper_get_positions(account_id: str):
    return {"status": 200, "msg": "success", "data": {}}


def wrapper_trade_operation(
    account_id: str,
    security: str,
    price: float,
    volume: int,
    order_side: OrderSide,
    bid_type: BidType,
):
    casename = global_case_data["case"]
    items = global_case_data["items"]
    index = global_case_data["index"]
    exec_flag = global_case_data["executed"]

    trade_operation = items[index]
    if trade_operation is None or "test_action" not in trade_operation:
        return {"status": 400, "msg": "no test_action defined in case stage"}

    if "parameters" not in trade_operation or "trade_result" not in trade_operation:
        return {
            "status": 400,
            "msg": "parameters and trade_result in trade operation not defined",
        }

    if order_side == OrderSide.BUY:
        if (bid_type == BidType.LIMIT and trade_operation["test_action"] != "buy") or (
            bid_type == BidType.MARKET
            and trade_operation["test_action"] != "market_buy"
        ):
            return {
                "status": 400,
                "msg": f"action not matched, {casename}, {trade_operation['stage']}, {trade_operation['test_action']}",
            }

    if order_side == OrderSide.SELL:
        if (bid_type == BidType.LIMIT and trade_operation["test_action"] != "sell") or (
            bid_type == BidType.MARKET
            and trade_operation["test_action"] != "market_sell"
        ):
            return {
                "status": 400,
                "msg": f"action not matched, {casename}, {trade_operation['stage']}, {trade_operation['test_action']}",
            }

    if exec_flag == 1:
        return {
            "status": 400,
            "msg": f"current action already executed, {casename} -> {trade_operation['stage']}, {trade_operation['test_action']}",
        }

    params = trade_operation["parameters"]
    data = trade_operation["trade_result"]

    code_in_action = params["code"]
    price_in_action = params["price"]
    volume_in_action = params["volume"]

    if (
        security == code_in_action
        and volume == volume_in_action
        and math.isclose(price, price_in_action, rel_tol=1e-5)
    ):
        # 设置当前步骤已执行
        execute_entrust_case(trade_operation)
        return {"status": 200, "msg": "success", "data": data}
    else:
        return {
            "status": 400,
            "msg": f"parameters in trade operation not matched, {casename} -> {trade_operation['stage']}",
        }


def wrapper_cancel_entrust(account_id: str, entrust_no: str):
    casename = global_case_data["case"]
    items = global_case_data["items"]
    index = global_case_data["index"]
    exec_flag = global_case_data["executed"]

    trade_operation = items[index]
    if trade_operation is None or "test_action" not in trade_operation:
        return {"status": 400, "msg": "no test_action defined in case stage"}

    if "parameters" not in trade_operation or "trade_result" not in trade_operation:
        return {
            "status": 400,
            "msg": "parameters and trade_result in trade operation not defined",
        }

    if trade_operation["test_action"] != "cancel_entrust":
        return {
            "status": 400,
            "msg": f"action not matched, {casename}, {trade_operation['stage']}, {trade_operation['stage']}",
        }

    if exec_flag == 1:
        return {
            "status": 400,
            "msg": f"current action already executed, {casename} -> {trade_operation['stage']}, {trade_operation['test_action']}",
        }

    params = trade_operation["parameters"]
    data = trade_operation["trade_result"]

    entrust_in_action = params["entrust_no"]

    if entrust_no == entrust_in_action:
        # 设置当前步骤已执行
        execute_entrust_case(trade_operation)
        return {"status": 200, "msg": "success", "data": data}
    else:
        return {
            "status": 400,
            "msg": f"parameters in trade operation not matched, {casename} -> {trade_operation['stage']}",
        }


def wrapper_get_today_entrusts():
    entrusts = global_accunt_info["entursts"]
    if len(entrusts) == 0:
        return {"status": 200, "msg": "success", "data": []}

    return {"status": 200, "msg": "success", "data": entrusts}


def wrapper_get_today_trades():
    trades = global_accunt_info["trades"]
    if len(trades) == 0:
        return {"status": 200, "msg": "success", "data": []}

    return {"status": 200, "msg": "success", "data": trades}
