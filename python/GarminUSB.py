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
        res = dev.get_course_limits()
        log.debug('res: %s', res )

        dev.get_fitness_profile()
        dev.get_workouts()
        dev.get_time()
        almanac = dev.get_almanac()
        log.debug('found %d almanac', len(almanac))
        runs = dev.get_runs()
        log.debug('found %d runs', len(runs[0]))
    finally:
        dev.close()

if __name__=='__main__':
    try:
        main()
    except Exception,ex:
        log.exception(ex)
