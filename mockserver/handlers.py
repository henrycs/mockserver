import datetime
import logging
import math
import uuid

from mockserver.trade import BidType, OrderSide

logger = logging.getLogger(__name__)

# 账号基本信息
global_accunt_info = {"info": {}, "entursts": {}}

# 加载的测试用例，为了简化设计，不允许股票代码重复
# 'uuid':{'items': [], 'executed': 0, 'index': -1, 'code': 'xxx''}
global_case_data = {}
global_case_exec_list = []


# /reset, /clear
def wrapper_reset_exec_data(clear_all: bool):
    # 清除所有执行记录
    global global_case_exec_list, global_case_data, global_accunt_info

    if clear_all:
        global_accunt_info["entursts"] = {}

    global_case_data = {}
    global_case_exec_list = []


# /current
def wrapper_current_stage(casename):
    # 读取当前正在执行的用例步骤
    casedata = global_case_data[casename]
    if casedata is None:
        return {"status": 400, "msg": "no test case loaded"}

    index = casedata["index"]
    if index == -1:
        return {"status": 400, "msg": "no test case loaded"}

    exec_flag = casedata["executed"]
    items = casedata["items"]
    item = items[index]

    return {
        "status": 200,
        "msg": "success",
        "data": {
            "code": casedata["code"],
            "stage": item["stage"],
            "action": item["test_action"],
            "executed": exec_flag,
        },
    }


# /history
def wrapper_exec_history():
    return {"status": 200, "msg": "success", "data": global_case_exec_list}


def validate_action_before_executed(casedata):
    code = casedata["code"]
    items = casedata["items"]
    current_index = casedata["index"]

    if current_index == -1:  # 尚未加载用例
        return {"status": 400, "msg": f"no case file loaded, {code}"}
    
    # 最后一个步骤已经执行了
    exec_flag = casedata["executed"]    
    if current_index == len(items) - 1 and exec_flag == 1:
        item = items[current_index]
        last_stage = item["stage"]
        return {
            "status": 400,
            "msg": f"no more stages, last stage, {code}:{last_stage}",
        }

    # 如果当前步骤已执行
    if exec_flag == 1:
        item = items[current_index]
        last_stage = item["stage"]
        action = item["test_action"]
        return {
            "status": 400,
            "msg": f"current action already executed: {code}->{last_stage}: {action}",
        }

    return {"status": 200, "msg": "OK"}


# /proceed
def wrapper_proceed_non_trade_action(casename):
    casedata = global_case_data[casename]
    if casedata is None:
        return {"status": 400, "msg": "no test case loaded"}

    # 检查case的当前执行情况
    result = validate_action_before_executed(casedata)
    if result["status"] != 200:
        return result

    items = casedata["items"]
    
    # 执行下一个测试步骤    
    item = items[casedata["index"]]
    current_stage = item["stage"]
    action = item["test_action"]

    #  如果是委托更新，则立刻执行
    if action == "entrust_update":
        execute_entrust_case(casedata, item)
        proceed_to_nextstep(casedata)
        return {
            "status": 200,
            "msg": "OK",
            "data": {
                "code": casedata["code"],
                "stage": current_stage,
                "action": action,
                "status": "action executed",
            },
        }

    return {
        "status": 400,
        "msg": f"action not matched, {casename}, {current_stage}, {action}",
    }


def proceed_to_nextstep(casedata):
    # 推进到下一个测试步骤，待执行
    code = casedata["code"]
    items = casedata["items"]
    current_index = casedata["index"]

    # 尚未加载用例
    if current_index == -1:
        logger.info(f"no case file loaded, {code}")
        return None

    # 最后一个步骤已经执行了
    if current_index == len(items) - 1:
        item = items[current_index]
        last_stage = item["stage"]
        logger.info(f"no more stages, last stage: {code}:{last_stage}")
        return None

    # 跳到下一个步骤
    exec_flag = casedata["executed"]
    if exec_flag == 1:
        casedata["index"] = current_index + 1
        casedata["executed"] = 0
        return 0
    else:
        logger.warning("current stage not executed, cannot proceed to next step")
        return None


# 执行委托更新，同步更新交易信息
def execute_entrust_case(casedata, item):
    datalist = []

    # 读取委托更新的内容
    if "entrust_update" in item:
        tmp = item["entrust_update"]
        datalist.append(tmp)

    if "trade_result" in item:
        tmp = item["trade_result"]
        datalist.append(tmp)

    for data in datalist:
        entrust_id = data["entrust_no"]
        entrusts = global_accunt_info["entursts"]
        entrusts[entrust_id] = data

    # 更新执行信息，记录历史步骤
    casedata["executed"] = 1
    global_case_exec_list.append(
        {
            "code": casedata["code"],
            "stage": item["stage"],
            "action": item["test_action"],
        }
    )

    return 0


def wrapper_load_case_data(casedata: list):
    tempname = uuid.uuid4().hex
    return initialize_case_data(casedata, tempname)


def get_code_from_casedata(items: list):
    for item in items:
        if "entrust_update" in item:
            data = item["entrust_update"]
            return data["code"]
        if "trade_result" in item:
            data = item["trade_result"]
            return data["code"]
    return None


def no_stages_in_case(casedata):
    items = casedata["items"]
    current_index = casedata["index"]

    # 尚未加载用例
    if current_index == -1:
        return False

    # 最后一个步骤已经执行了
    if current_index == len(items) - 1:
        return True
    
    return False


def initialize_case_data(items: list, casename: str):
    global global_case_data
    if casename in global_case_data:
        logger.warning(f"case {casename} already exists")
        return {"status": 400, "msg": "duplicated case name"}

    # 判断股票代码是否重复，不同的case不允许重复
    codes = []
    to_be_deleted = []
    for _casename in global_case_data:
        casedata = global_case_data[_casename]        
        if no_stages_in_case(casedata):
            to_be_deleted.append(_casename)
            continue

        tmp = casedata["items"]
        code = get_code_from_casedata(tmp)
        codes.append(code)
    for _key in to_be_deleted:
        del global_case_data[_key]

    newcode = get_code_from_casedata(items)
    if newcode in codes:
        logger.warning(f"code {newcode} already exists")
        return {"status": 400, "msg": "duplicated code"}

    # 解析测试步骤
    if len(items) == 0:
        logger.error("no content found in case file")
        return {"status": 400, "msg": "no content in case file"}

    # 取当前时间
    now = datetime.datetime.now()
    datestr = now.strftime("%Y-%m-%d %H:%M:%S.%f")

    if len(items) == 1:  # 单个买卖动作，动态更新ID
        item = items[0]
        action_name = item["test_action"]
        if action_name.find("buy") >= 0 or action_name.find("sell") >= 0:
            trade_result = item["trade_result"]
            trade_result["entrust_no"] = str(uuid.uuid4())
            trade_result["eid"] = str(uuid.uuid4())

    # 更新委托信息中的时间为当前时间
    for item in items:
        if "entrust_update" in item:
            data = item["entrust_update"]
            data["time"] = datestr
            data["recv_at"] = datestr
        if "trade_result" in item:
            data = item["trade_result"]
            data["time"] = datestr
            data["recv_at"] = datestr

    try:
        casedata = {"code": newcode}
        casedata["items"] = items
        global_case_data[casename] = casedata

        # 前进到第一个用例
        casedata["index"] = 0
        casedata["executed"] = 0

        item = items[0]
        act_result = "to be executed"
        current_stage = item["stage"]
        current_action = item["test_action"]

        # 如果第一个用例是委托更新，则自动执行
        if item["test_action"] == "entrust_update":
            execute_entrust_case(casedata, item)
            proceed_to_nextstep(casedata)
            act_result = "action executed"

        return {
            "status": 200,
            "msg": "OK",
            "data": {
                "case": casename,
                "stage": current_stage,
                "action": current_action,
                "status": act_result,
            },
        }
    except Exception as e:
        logger.error(e)
        return {"status": 500, "msg": e}


def wrapper_get_balance(account_id: str):
    acct_info = global_accunt_info["info"]
    return {"status": 200, "msg": "success", "data": acct_info}


def wrapper_get_positions(account_id: str):
    positions = global_accunt_info["posistions"]
    if len(positions) == 0:
        return {"status": 200, "msg": "success", "data": []}

    data = [i for i in positions.values()]
    return {"status": 200, "msg": "success", "data": data}


def get_casedata_via_code(code):
    for casename in global_case_data:
        casedata = global_case_data[casename]
        if code == casedata["code"]:
            return casedata

    return None


def get_casedata_via_cid(cid):
    for casename in global_case_data:
        casedata = global_case_data[casename]
        items = casedata["items"]
        for item in items:
            if "parameters" in item:
                parameters = item["parameters"]
                if "entrust_no" in parameters and parameters["entrust_no"] == cid:
                    return casedata

    return None


# ------------------------------- 交易指令 ---------------------------------------


def wrapper_trade_operation(
    account_id: str,
    security: str,
    price: float,
    volume: int,
    order_side: OrderSide,
    bid_type: BidType,
):
    casedata = get_casedata_via_code(security)
    if casedata is None:
        return {"status": 400, "msg": "invalid security"}

    result = validate_action_before_executed(casedata)
    if result["status"] != 200:
        return result

    items = casedata["items"]
    index = casedata["index"]

    trade_operation = items[index]
    if trade_operation is None or "test_action" not in trade_operation:
        return {"status": 400, "msg": "no test_action defined in case stage"}

    if order_side == OrderSide.BUY:
        if (bid_type == BidType.LIMIT and trade_operation["test_action"] != "buy") or (
            bid_type == BidType.MARKET
            and trade_operation["test_action"] != "market_buy"
        ):
            return {
                "status": 400,
                "msg": f"action not matched, {security}, {trade_operation['stage']}, {trade_operation['test_action']}",
            }

    if order_side == OrderSide.SELL:
        if (bid_type == BidType.LIMIT and trade_operation["test_action"] != "sell") or (
            bid_type == BidType.MARKET
            and trade_operation["test_action"] != "market_sell"
        ):
            return {
                "status": 400,
                "msg": f"action not matched, {security}, {trade_operation['stage']}, {trade_operation['test_action']}",
            }

    if "parameters" not in trade_operation or "trade_result" not in trade_operation:
        return {
            "status": 400,
            "msg": "parameters and trade_result in trade operation not defined",
        }

    params = trade_operation["parameters"]
    data = trade_operation["trade_result"]

    code_in_action = params["code"]
    price_in_action = params["price"]
    volume_in_action = params["volume"]

    if bid_type == BidType.MARKET:
        price_in_action = 0
        price = 0

    if (
        security == code_in_action
        and volume == volume_in_action
        and math.isclose(price, price_in_action, rel_tol=1e-5)
    ):
        # 设置当前步骤已执行
        execute_entrust_case(casedata, trade_operation)
        # 跳到下一个步骤
        proceed_to_nextstep(casedata)
        return {"status": 200, "msg": "success", "data": data}
    else:
        return {
            "status": 400,
            "msg": f"parameters in trade operation not matched, {security} -> {trade_operation['stage']}",
        }


def wrapper_cancel_entrust(account_id: str, entrust_no: str):
    casedata = get_casedata_via_cid(entrust_no)
    if casedata is None:
        return {"status": 400, "msg": "invalid entrust id"}

    result = validate_action_before_executed(casedata)
    if result["status"] != 200:
        return result

    code = casedata["code"]
    items = casedata["items"]
    index = casedata["index"]
    exec_flag = casedata["executed"]

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
            "msg": f"action not matched, {code}, {trade_operation['stage']}, {trade_operation['stage']}",
        }

    if exec_flag == 1:
        return {
            "status": 400,
            "msg": f"current action already executed, {code} -> {trade_operation['stage']}, {trade_operation['test_action']}",
        }

    params = trade_operation["parameters"]
    data = trade_operation["trade_result"]

    entrust_in_action = params["entrust_no"]
    if isinstance(entrust_in_action, list) or entrust_in_action != entrust_no:
        return {
            "status": 400,
            "msg": f"parameters in trade operation not matched, {code} -> {trade_operation['stage']}",
        }

    # 设置当前步骤已执行
    execute_entrust_case(casedata, trade_operation)
    # 跳到下一个步骤
    proceed_to_nextstep(casedata)

    return {"status": 200, "msg": "success", "data": data}


def wrapper_get_today_entrusts(entrust_list):
    db_entrusts = global_accunt_info["entursts"]
    if len(db_entrusts) == 0:
        return {"status": 200, "msg": "success", "data": {}}

    if entrust_list is None or len(entrust_list) == 0:
        return {"status": 200, "msg": "success", "data": db_entrusts}

    out_entrusts = {}
    keys = db_entrusts.keys()
    for entrust in entrust_list:
        if entrust in keys:
            out_entrusts[entrust] = db_entrusts[entrust]
    return {"status": 200, "msg": "success", "data": out_entrusts}


def wrapper_get_today_trades():
    trades = global_accunt_info["trades"]
    if len(trades) == 0:
        return {"status": 200, "msg": "success", "data": []}

    out_trades = {}
    for entrust_no in trades:
        out_trades[entrust_no] = trades[entrust_no]
    return {"status": 200, "msg": "success", "data": out_trades}
