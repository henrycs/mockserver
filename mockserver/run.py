# -*- coding: utf-8 -*-
# @Author   : henry
# @Time     : 2022-03-09 15:08
import logging
import os
from os import path

import cfg4py

from mockserver.server import server_start

logger = logging.getLogger(__name__)


def init_logger(filename: str, loglevel: int):
    LOG_FORMAT = r"%(asctime)s %(levelname)s %(filename)s[line:%(lineno)d] %(message)s"
    DATE_FORMAT = r"%Y-%m-%d  %H:%M:%S %a"

    fh = logging.FileHandler(filename, mode="a+")
    fh.setLevel(loglevel)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    fh.setFormatter(formatter)

    logging.basicConfig(
        level=logging.DEBUG, format=LOG_FORMAT, datefmt=DATE_FORMAT, handlers=[fh]
    )


def start():
    cur_dir = path.dirname(__file__)

    # init config instance
    config_dir = path.normpath(path.join(cur_dir, "config"))
    print(f"configuration folder: {config_dir}")

    if not os.path.exists(config_dir):
        print("configuration file not found or invalid")
        return

    cfg4py.init(config_dir, False)

    # read configuration and init server
    server_config = cfg4py.get_instance()
    loglevel = server_config.log_level
    logfile = path.normpath(path.join(cur_dir, "server.log"))
    init_logger(logfile, loglevel)

    logger.info("mock trade server start .......")
    server_start()


if __name__ == "__main__":
    start()
