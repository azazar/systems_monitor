#!/usr/bin/python3


import os
import json


def find_mount_point(path):
    path = os.path.abspath(path)
    while not os.path.ismount(path):
        path = os.path.dirname(path)
    return path


def get_space_left(file):
    """
    Get space left on partition
    """

    stats = os.statvfs(file)
    bsize = stats.f_bsize

    return (stats.f_bavail * bsize, stats.f_blocks * bsize)


stats = {}

# Get available space on /home and root

paths = [os.environ['HOME'], '/']

stats['df'] = {}
for path in paths:
    mountpoint = find_mount_point(path)
    stats['df'][mountpoint] = get_space_left(path)

num_cpus = os.cpu_count()
stats['la'] = [avg / num_cpus for avg in os.getloadavg()]

free = os.popen('free').read().split('\n')[1:]
stats['avail_mem'] = int(free[0].split()[6]) / int(free[0].split()[1])
stats['free_swap'] = int(free[1].split()[3]) / int(free[1].split()[1])

print(json.dumps(stats))
