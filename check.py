#!/usr/bin/python3


import sys
import os
import subprocess
import json
import urllib.request
import time
import xml.etree.ElementTree as ET


servers_to_monitor = ['m@b.uo1.net', 'm@n.uo1.net', 'm@bitcoinfaucet.uo1.net']
ok_https_to_monitor = {
    'https://bitcoinfaucet.uo1.net/site_status.php': 'm@bitcoinfaucet.uo1.net',
    'https://fatxxx.tube/test': 'fvs@fvs',
    'https://freeporntube.tv/test': 'fvs@fvs',
    'https://indian-porn-tube.mobi/test': 'fvs@fvs',
}


def alert(message, ssh_userhost=None):
    """
    Send alert to server
    """

    if ssh_userhost is not None:
        message = '{}<click>autoterm -e ssh {}</click>'.format(message, ssh_userhost)

    print('<txt><span foreground="#FF7777">{}</span></txt>'.format(message))
    exit(0)


def check_alert(check_func, ssh_userhost=None):
    """
    Check if alert is needed
    """
    (is_ok, errors) = check_func()

    if not is_ok:
        alert(errors, ssh_userhost)


def ping_check(host):
    """
    Check if host is up
    """
    ping_cmd = 'ping -c 1 {}'.format(host)
    (exitcode, output) = subprocess.getstatusoutput(ping_cmd)

    if exitcode != 0:
        return (False, 'Failed to ping {}'.format(host))

    return (True, None)


def check_server(ssh_userhost):
    """
    Check if server is up and running using OpenSSH client
    """
    host = ssh_userhost.split('@')[1]
    ssh_cmd = 'ssh {} python3 - < {}/print_stats.py'.format(ssh_userhost, os.path.dirname(os.path.realpath(__file__)))

    (exitcode, output) = subprocess.getstatusoutput(ssh_cmd)

    if exitcode != 0:
        return (False, '{}: Failed to fetch stats'.format(host))

    errors = []
    status = json.loads(output)

    if type(status) != dict:
        return (False, '{}: Failed to parse stats ({} returned)'.format(host, type(status)))

    for partition in status['df']:
        kbytes_avail = status['df'][partition][0]
        kbytes_total = status['df'][partition][0]
        if kbytes_avail < 1024*1024*1024*1 or kbytes_avail < kbytes_total * 0.1:
            errors.append('{} {} has just {:.2f} GiB bytes left'.format(host, partition, status['df'][partition] / 1024 / 1024 / 1024))

    if status['la'][2] > 0.5:
        errors.append('{} la is {:.2f}'.format(host, status['la'][2]))

    if status['avail_mem'] < 0.25:
        errors.append('{} free memory is {:.2f}%'.format(host, status['avail_mem'] * 100))

    if status['free_swap'] < 0.5:
        errors.append('{} free swap is {:.2f}%'.format(host, status['free_swap'] * 100))

    return (len(errors) == 0, ", ".join(errors))


def urlopen(url):
    req = urllib.request.Request(
        url,
        data=None,
        headers={
            'User-Agent': 'UptimeRobot/1.0'
        }
    )

    return urllib.request.urlopen(req)


def check_http_ok(url):
    """
    Check if HTTP request returns 200 OK
    """
    try:
        with urlopen(url) as response:
            if response.code != 200:
                return (False, '{}: HTTP request failed with code {}'.format(url, response.code))

            contents = response.read()

            if contents != b'OK':
                return (False, '{}: {}'.format(url, contents))

            return (True, None)
    except Exception as e:
        return (False, 'Failed to check {} ({})'.format(url, e))


def check_http_contains(url, text):
    """
    Check if HTTP request returns 200 OK
    """
    try:
        with urlopen(url) as response:
            if response.code != 200:
                return (False, '{}: HTTP request failed with code {}'.format(url, response.code))

            contents = response.read()

            if contents.decode('utf-8').find(text) == -1:
                return (False, '{}: "{}" not found'.format(url, text))

            return (True, None)
    except Exception as e:
        return (False, 'Failed to check {} ({})'.format(url, e))


def check_dynadot_expiring_domains(api_key):
    """
    Check if Dynadot has expiring domains
    """
    url = 'https://api.dynadot.com/api3.xml?key={}&command=list_domain'.format(api_key)
    ditch_domains = ['1st-class.faith']
    try:
        with urlopen(url) as response:
            if response.code != 200:
                return (False, 'Dynadot HTTP request failed with code {}'.format(response.code))

            # create element tree object
            tree = ET.parse(response)

            # get root element
            root = tree.getroot()

            errors = []

            domain_items = root.findall('ListDomainInfoContent/DomainInfoList/DomainInfo/Domain')

            for domain_item in domain_items:
                name = domain_item.find('Name').text

                if name in ditch_domains:
                    continue

                expiry_days = int(int(domain_item.find('Expiration').text) / 1000 - int(time.time())) / (60 * 60 * 24)

                if expiry_days < 183:
                    errors.append('Dynadot domain {} is expiring in {} days'.format(name, expiry_days))

            return (len(errors) == 0, ", ".join(errors))
    except Exception as e:
        return (False, 'Failed to check {} ({})'.format(url, e))


check_alert(lambda: ping_check('1.1.1.1'))

if len(sys.argv) >= 2:
    check_alert(lambda: check_dynadot_expiring_domains(sys.argv[1]))

for server in servers_to_monitor:
    check_alert(lambda: check_server(server), server)

for url in ok_https_to_monitor:
    check_alert(lambda: check_http_ok(url), ok_https_to_monitor[url])

check_alert(lambda: check_http_contains('https://fbsearch.ru/', '<title>FBSearch - настоящий книжный поисковик</title>'), 'm@fbsearch')

print('<txt><span foreground="#00FF77">✓</span></txt>')
