import json
import pathlib
import re
from collections import OrderedDict
from rffe_uc import RFFEuC_Test

ip_ends = [i for i in range(201,214)]
#ip_base = '192.168.0.'
ip_base = '10.0.18.'

#Code from Chris Olds @ http://code.activestate.com/recipes/442460/
def increment(s):
    """ look for the last sequence of number(s) in a string and increment """
    lastNum = re.compile(r'(?:[^\d]*(\d+)[^\d]*)+')
    m = lastNum.search(s)
    if m:
        next = str(int(m.group(1))+1)
        start, end = m.span(1)
        s = s[:max(end-len(next), start)] + next + s[end:]
    return s

def increment_ip(s):
    if (int(s.split('.')[-1]) +1) in ip_ends:
        return increment(s)
    else:
        return ip_base+'201'

def increment_mac(m):
    return format((int(m,16)+1), '012X')

ip_sn_table_path = pathlib.Path('ip_sn_table.json')
try:
    ip_sn_table_path.resolve()
    with ip_sn_table_path.open('r') as json_f:
        ip_sn_table = json.loads(json_f.read(), object_pairs_hook=OrderedDict)
        last_sn = list(ip_sn_table.keys())[-1]
        next_sn = increment(last_sn)
        last_ip = ip_sn_table[last_sn]['ip']
        next_ip = increment_ip(last_ip)
        last_mac = ip_sn_table[last_sn]['mac'].replace(':','')
        next_mac = increment_mac(last_mac)
except FileNotFoundError:
    print('"ip_sn_table.json file not found! A new one will be created')
    next_sn = 'CN00001'
    next_ip = ip_base+'201'
    next_mac = '20000000001'

op_name = input('Operator name: ')
override = input('Override initial board informations? (default:"'+next_sn+'" "'+next_ip+'" "'+next_mac+'"): [y/N] ')
if override.lower() == 'y':
    override_sn = input('SN: ')
    if override_sn != '':
        next_sn = override_sn
        override_ip = input('IP: ')
    if override_ip != '':
        next_ip = override_ip
        override_mac = input('MAC: ')
    if override_mac != '':
        next_mac = override_mac

seq = input('Should the test run [c]ontinuously or just [o]ne time? (default: "c"): ')
if seq == '':
    #Default to continuous
    seq = 'c'

while True:
    print('Testing -> Ip: {} MAC: {} SN: {}'.format(next_ip, next_mac, next_sn))
    uc = RFFEuC_Test((next_ip, '255.255.255.0', ip_base+'1', next_mac), '/dev/ttyUSB0', op_name, 'RFFEuC:1.2', next_sn)
    result = uc.run()
    print('\nResult: '+('PASS!' if result else 'FAIL!')+'\n')

    open_mode = 'r+' if ip_sn_table_path.is_file() else 'w+'
    with ip_sn_table_path.open(open_mode) as ip_sn_table_f:
        ip_sn_table_str = ip_sn_table_f.read()
        if (ip_sn_table_str):
            ip_sn_table = json.loads(ip_sn_table_str, object_pairs_hook=OrderedDict)
        else:
            ip_sn_table = OrderedDict()
        ip_sn_table[next_sn] = OrderedDict([('ip',uc.test_results['ethernet']['deployIP']),('mac',uc.test_results['ethernet']['mac']),('result','pass' if result else 'fail')])
        ip_sn_table_f.seek(0)
        json.dump(ip_sn_table, ip_sn_table_f, indent=4, ensure_ascii=True)
        ip_sn_table_f.truncate()

    if seq == 'o':
        break
    i = input('Start next test? (IP:{} MAC:{} SN:{}) [Y/n][r]epeat: '.format(increment_ip(next_ip),increment_mac(next_mac),increment(next_sn)))
    if i.lower() == 'n':
        break

    if i.lower() != 'r':
        next_ip = increment_ip(next_ip)
        next_mac = increment_mac(next_mac)
        next_sn = increment(next_sn)
