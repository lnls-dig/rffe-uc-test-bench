import socket
import time
import serial
import re
import json
import datetime
import subprocess
import os
import pathlib
from collections import OrderedDict
#import pprint

from report import RFFEuC_Report

class RFFEuC_Test(object):

    def __init__(self, eth_conf, serial_port, operator, test_board_sn, board_sn, test_mask_path='mask.json'):
        self.ser = serial.Serial(serial_port, 115200)
        self.eth_ip = eth_conf[0]
        self.eth_mask = eth_conf[1]
        self.eth_gateway = eth_conf[2]
        self.eth_mac = eth_conf[3].replace(":","")
        with open(test_mask_path) as mask_f:
            self.test_mask = json.loads(mask_f.read())
        self.test_results = OrderedDict()
        self.log = []
        self.test_results['Operator'] = operator
        self.test_results['Date'] = str(datetime.datetime.today())
        self.test_results['Testboard SN'] = str(test_board_sn)
        self.test_results['Board SN'] = str(board_sn)
        self.test_results['Test SW commit'] = subprocess.check_output(["git", "describe", "--always"]).strip().decode('ascii')

    def eth_connect(self):
        self.eth_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.eth_sock.connect((self.eth_ip, 6791))
        except:
            raise

    def eth_test(self):
        self.eth_connect()
        self.eth_sock.send(b"Test msg!\0")
        self.eth_sock.shutdown(socket.SHUT_RDWR)
        self.eth_sock.close()

    def run(self):
        self.log = []
        self.ser.flush()

        #Reset RFFEuC
        self.ser.setDTR(True)
        self.ser.setRTS(False)
        time.sleep(0.1)
        self.ser.setRTS(True)
        time.sleep(0.1)

        #Start tests
        self.ser.write(b's')
        ln = self.ser.read(50)

        while True:
            ln = self.ser.readline().decode('ascii')
            self.log.append(ln)
            if (ln.find("Insert MAC:") > -1):
                self.ser.write(bytes(self.eth_mac+'\r\n','ascii'))
            elif (ln.find("Insert IP:") > -1):
                self.ser.write(bytes(self.eth_ip+'\n','ascii'))
            elif (ln.find("Insert Mask:") > -1):
                self.ser.write(bytes(self.eth_mask+'\n','ascii'))
            elif (ln.find("Insert Gateway:") > -1):
                self.ser.write(bytes(self.eth_gateway+'\n','ascii'))
            elif (ln.find("Listening on port: 6791") > -1):
                self.eth_test()
            elif (ln.find("End of tests!") > -1):
                break

    def LED_parse(self):
        ind = [i for i, elem in enumerate(self.log) if '[LED]' in elem]
        self.test_results['LED'] = OrderedDict()
        for i in ind:
            regex = re.findall(r"\d*\.?\d+", self.log[i])
            if len(regex) > 0:
                self.test_results['LED'][regex[0]] = {'value':float(regex[1])}
                self.test_results['LED'][regex[0]]['result'] = (1 if self.test_results['LED'][regex[0]]['value'] < self.test_mask['LED']['mask'] else 0)
        #Set the general result to 1 if all the tests passed
        res = 1
        for k,v in self.test_results['LED'].items():
            for k1,v1 in v.items():
                if (k1 == 'result'):
                    res &= v1
        self.test_results['LED']['result'] = res

    def GPIOLoopback_parse(self):
        self.test_results['GPIO'] = OrderedDict()
        ind = [i for i, elem in enumerate(self.log) if 'Loopback' in elem]
        result = []
        for t, i in enumerate(ind):
            loop_pair = re.findall(r"\[([^]]+)\]", self.log[i])
            loop_res = re.findall("(Pass|Fail)", self.log[i])
            if len(loop_pair) > 0:
                result.append([loop_pair, (1 if loop_res[0] == 'Pass' else 0)])
                self.test_results['GPIO'][t] = {'pin1':loop_pair[0],'pin2':loop_pair[1],'result':(1 if loop_res[0] == 'Pass' else 0)}
        #Set the general result to 1 if all the tests passed
        res = 1
        for k,v in self.test_results['GPIO'].items():
            for k1,v1 in v.items():
                if (k1 == 'result'):
                    res &= v1
        self.test_results['GPIO']['result'] = res


    def PowerSupply_parse(self):
        ind = [i for i, elem in enumerate(self.log) if 'Power Supply' in elem]
        self.test_results['PS'] = OrderedDict()
        for i in ind:
            regex = re.findall(r"\d*\.?\d+", self.log[i])
            if len(regex) > 0:
                self.test_results['PS'][regex[0]] = {'value':float(regex[1])}
                low = self.test_mask['PS'][regex[0]]['nominal'] - self.test_mask['PS'][regex[0]]['tolerance']
                high = self.test_mask['PS'][regex[0]]['nominal'] + self.test_mask['PS'][regex[0]]['tolerance']
                self.test_results['PS'][regex[0]]['result'] = (1 if (low <= float(regex[1]) <= high) else 0)
        #Set the general result to 1 if all the tests passed
        res = 1
        for k,v in self.test_results['PS'].items():
            for k1,v1 in v.items():
                if (k1 == 'result'):
                    res &= v1
        self.test_results['PS']['result'] = res

    def FeRAM_parse(self):
        ind = [i for i, elem in enumerate(self.log) if '[RANDOM]' in elem]
        rand = []
        for i in ind:
            regex = re.findall(r'[0-9a-fA-F][0-9a-fA-F]', self.log[i])
            if len(regex) > 0:
                rand.extend(regex)

        ind = [i for i, elem in enumerate(self.log) if '[FERAM]' in elem]
        result = []
        for i in ind:
            regex = re.findall("(Pass|Fail)", self.log[i])
            if len(regex) > 0:
                result.append(1 if regex[0] == 'Pass' else 0)
        self.test_results['FERAM'] = {'pattern': ''.join(rand), 'result': result[0]}

    def Ethernet_parse(self):
        self.test_results['ETHERNET'] = OrderedDict()
        ind = [i for i, elem in enumerate(self.log) if 'Received:' in elem]
        for i in ind:
            regex = re.findall(r'"(.*?)"', self.log[i])
            if len(regex) > 0:
                self.test_results['ETHERNET']['message'] = regex[0]
        self.test_results['ETHERNET']['result'] = 1 if self.test_results['ETHERNET']['message'] == self.test_mask['ETHERNET']['message'] else 0
        self.test_results['ETHERNET']['MAC'] = ':'.join([self.eth_mac[i:i+2] for i in range(0, len(self.eth_mac), 2)])
        self.test_results['ETHERNET']['IP'] = self.eth_ip
        self.test_results['ETHERNET']['Gateway'] = self.eth_gateway
        self.test_results['ETHERNET']['Mask'] = self.eth_mask

    def dump(self, path):
        dump_abs = os.path.abspath(os.path.expanduser(path))
        pathlib.Path(os.path.dirname(dump_abs)).mkdir(parents=True, exist_ok=True)
        with open(dump_abs, 'w') as dump_f:
            json.dump(self.test_results, dump_f, indent=4, ensure_ascii=True)

if __name__ == "__main__":
    uc = RFFEuC_Test(("10.0.18.111", "255.255.255.0", "10.0.18.1", "DE:AD:BE:EF:12:34"), "/dev/ttyUSB0", 'Henrique Silva', 'TST0001','UC0001')
    uc.run()

    uc.LED_parse()
    uc.GPIOLoopback_parse()
    uc.PowerSupply_parse()
    uc.Ethernet_parse()
    uc.FeRAM_parse()
    uc.dump('./test_report/results.json')
    #pp = pprint.PrettyPrinter(indent=4)
    #pp.pprint(uc.test_results)

    rep = RFFEuC_Report(uc.test_results, "0", "1")
    rep.generate('./test_report')
