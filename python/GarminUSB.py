#!/usr/bin/python
import logging

from garmin.device import Forerunner

log = logging.getLogger('main')

def init_logging ():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(levelname)s %(name)s: %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def main():
    init_logging()
    dev = Forerunner()
    try:
        dev.start_session()
        dev.get_device_capabilities()
        dev.get_fitness_profile()
        dev.get_workouts()
        dev.get_time()
        #dev.get_runs()
    finally:
        dev.close()

if __name__=='__main__':
    try:
        main()
    except Exception,ex:
        log.exception(ex)
