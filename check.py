#!/usr/bin/python3


import os
import subprocess
import json
import urllib.request
import time
import xml.etree.ElementTree as ET
import shlex


def alert(message, ssh_userhost=None):
    """
    Send alert to server
    """

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
    print_stats_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'print_stats.py')

    if 'sshCmd' in conf:
        ssh_cmd = conf['sshCmd']
    else:
        ssh_cmd = 'timeout 5s ssh -q -o BatchMode=yes'

    ssh_cmd = ssh_cmd + ' {} python3 - < {}'.format(ssh_userhost, print_stats_path)

    (exitcode, output) = subprocess.getstatusoutput(ssh_cmd)

    if exitcode != 0:
        return (False, '{}: Failed to fetch stats'.format(host))

    errors = []
    status = json.loads(output)

    if type(status) != dict:
        return (False, '{}: Failed to parse stats ({} returned)'.format(host, type(status)))

    for partition in status['df']:
        kbytes_avail = status['df'][partition][0]
        kbytes_total = status['df'][partition][1]
        if kbytes_avail < min(kbytes_total * 0.05, 16*1024*1024*1024):
            errors.append('{} on {} has just {:.2f} GiB left'.format('root' if partition == '/' else partition, host, status['df'][partition][0] / 1024 / 1024 / 1024))

    if status['la'][2] > 0.5:
        errors.append('{} la is {:.2f}'.format(host, status['la'][2]))

    if status['avail_mem'] < 0.1:
        errors.append('{} free memory is {:.2f}%'.format(host, status['avail_mem'] * 100))

    if status['free_swap'] < 0.1:
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


def check_dynadot_expiring_domains(api_key, warn_days=60):
    """
    Check if Dynadot has expiring domains
    """
    url = 'https://api.dynadot.com/api3.xml?key={}&command=list_domain'.format(api_key)
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
                renew = domain_item.find('RenewOption').text

                if renew != 'auto-renew':
                    continue

                name = domain_item.find('Name').text

                expiry_days = int((int(domain_item.find('Expiration').text) / 1000 - int(time.time())) / (60 * 60 * 24))

                if expiry_days < 0:
                    errors.append('Dynadot domain {} expired {} days ago'.format(name, -expiry_days))
                elif expiry_days < warn_days:
                    errors.append('Dynadot domain {} is expiring in {} days'.format(name, expiry_days))

            return (len(errors) == 0, ", ".join(errors))
    except Exception as e:
        return (False, 'Failed to check {} ({})'.format(url, e))


def check_custom_command(command, cwd):
    """
    Check if a custom command returns the expected return code
    """
    try:
        result = subprocess.run([os.environ['SHELL'], '-c', command], cwd=cwd, capture_output=True, text=True)

        if result.returncode != 0:
            err = str(result.stderr).strip()

            if err == '':
                err = str(result.stdout).strip()

                if err == '':
                    err = f"'{command}' returned {result.returncode}"

            return (False, err)

        return (True, None)
    except Exception as e:
        return (False, f"Failed to execute command '{command}': {str(e)}")


base_dir = os.path.dirname(os.path.realpath(__file__))
conf_path = os.path.join(base_dir, 'conf.json')
conf = json.load(open(conf_path))

check_alert(lambda: ping_check('1.1.1.1'))

if 'dynadot' in conf:
    dynadot_conf = conf['dynadot']

    if 'apiKey' in dynadot_conf:
        check_alert(lambda: check_dynadot_expiring_domains(dynadot_conf['apiKey'], dynadot_conf['warnDays']))

for url, ssh_userhost in conf['httpExpectOk'].items():
    check_alert(lambda: check_http_ok(url), ssh_userhost)

for url, text in conf['httpFind'].items():
    check_alert(lambda: check_http_contains(url, text))

for server in conf['sshServers']:
    check_alert(lambda: check_server(server), server)

for cmd in conf['customCommands']:
    check_alert(lambda: check_custom_command(cmd, base_dir))

print('<txt><span foreground="#00FF77">✓</span></txt>')
