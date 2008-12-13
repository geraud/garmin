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

def dump_one(item, indent = 0):
    log.debug('%s%s', '  '*indent,  item)

def dump_many(items, printer= None, prefix='', indent = 0 ):
    indentation = '  '* indent
    log.debug('%s dumping list of %d items', indentation, len(items) )
    for i, item in enumerate(items):
        log.debug( indentation + '%d %s:', i , prefix)
        (printer or dump_one)(item, indent = indent + 1 )

def main():
    init_logging()
    dev = Forerunner()
    try:
        dev.start_session()
        dev.get_device_capabilities()

        res = dev.get_courses()
        log.debug('res: %s', res )

        res = dev.get_course_points()
        dump_many(res, prefix ='course points')

        res = dev.get_course_laps()
        dump_many(res)

        res = dev.get_course_limits()
        log.debug('res: %s', res )
        res = dev.get_course_tracks()
        dump_many(res)

        res = dev.get_fitness_profile()
        dump_one(res)
        dev.get_workouts()
        dev.get_time()

        almanac = dev.get_almanac()
        log.debug('found %d almanac', len(almanac))
        runs,laps,c = dev.get_runs()
        log.debug("Runs:")
        dump_many(runs)
        log.debug("Laps:")
        dump_many(laps)
        log.debug("Track?:")
        dump_many(c)
    finally:
        dev.close()

if __name__=='__main__':
    try:
        main()
    except Exception,ex:
        log.exception(ex)
