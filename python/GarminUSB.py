#!/usr/bin/python
import os, sys, array, logging

from garmin.device import *

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
        # log.debug("device : %s",dev)
        # log.debug('protocols: %s', dev.protocols)
        dev.get_runs()
        dev.get_fitness_profile()

    finally:
        dev.close()

if __name__=='__main__':
    main()
