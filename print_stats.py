#!/usr/bin/python3


import os
import json


def get_space_left(partition):
    """
    Get space left on partition
    """

    stats = os.statvfs(partition)
    bsize = stats.f_bsize

    return (stats.f_bavail * bsize, stats.f_blocks * bsize)


stats = {}

# Get available space on /home and root

stats['df'] = {
    '/': get_space_left('/'),
    os.environ['HOME']: get_space_left(os.environ['HOME']),
}

num_cpus = os.cpu_count()
stats['la'] = [avg / num_cpus for avg in os.getloadavg()]

free = os.popen('free').read().split('\n')[1:]
stats['avail_mem'] = int(free[0].split()[6]) / int(free[0].split()[1])
stats['free_swap'] = int(free[1].split()[3]) / int(free[1].split()[1])

print(json.dumps(stats))
