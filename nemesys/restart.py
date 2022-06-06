from datetime import datetime
from threading import Thread
from time import sleep
import logging
import os

from common import utils


RESTART_HOUR = 0
RESTART_MINUTE = 55


class RestartScheduler(Thread):
    def run(self):
        if utils.is_windows():
            while True:
                logging.debug("Restart scheduler: checking time")
                n = datetime.now()
                if n.hour == RESTART_HOUR and n.minute == RESTART_MINUTE:
                    logging.info("Restart scheduler: restarting in 2 seconds")
                    sleep(2)
                    os._exit(1)
                sleep(50)
