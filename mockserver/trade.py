# -*- coding: utf-8 -*-
# @Author   : henry
# @Time     : 2022-03-09 15:08
import datetime
import uuid
from enum import IntEnum


class OrderSide(IntEnum):
    BUY = 1  # 股票买入
    SELL = -1  # 股票卖出


class BidType(IntEnum):
    LIMIT = 1  # 限价委托
    MARKET = 2  # 市价委托


class OrderStatus(IntEnum):
    ERROR = -1  # 异常
    RECEIVED = 0  # 待报
    SUBMITTED = 1  # 已报
    PARTIAL_TX = 2  # #部分成交
    ALL_TX = 3  # 全部成交
    CANCELED = 4  # 撤单
