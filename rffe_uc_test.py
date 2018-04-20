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
from lpc21isp import LPCProg
#import pprint

from report import RFFEuC_Report

class RFFEuC_Test(object):

    TEST_FW_PATH='../rffe-uc-test-fw/BUILD/rffe-uc-test-fw.bin'

    def __init__(self, eth_conf, serial_port, operator, test_board_sn, board_sn, test_mask_path='mask.json'):
        self.log = []
        self.serial_port = serial_port
        self.eth_ip = eth_conf[0]
        self.eth_mask = eth_conf[1]
        self.eth_gateway = eth_conf[2]
        self.eth_mac = eth_conf[3].replace(":","")

        with open(test_mask_path) as mask_f:
            self.test_mask = json.loads(mask_f.read())

        self.test_results = OrderedDict()
        self.test_results['operator'] = operator
        self.test_results['date'] = str(datetime.datetime.today())
        self.test_results['testBoardSN'] = str(test_board_sn)
        self.test_results['boardSN'] = str(board_sn)
        self.test_results['testSWCommit'] = subprocess.check_output(["git", "describe", "--always"]).strip().decode('ascii')

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

    def program_fw(self, fw):
        programmer = LPCProg(self.serial_port,bin_path='../lpc21isp/lpc21isp')
        print('Programming firmware to LPC...')
        programmer.program(fw)
        print('Sucess!')

    def run(self):
        self.program_fw(self.TEST_FW_PATH)

        print('Starting tests...')
        self.log = []
        ser = serial.Serial(self.serial_port, 115200)
        ser.flush()

        #Reset RFFEuC
        ser.setDTR(True)
        ser.setRTS(False)
        time.sleep(0.1)
        ser.setRTS(True)
        time.sleep(0.1)

        #Start tests
        ser.write(b's')
        ln = ser.read(50)

        while True:
            ln = ser.readline().decode('ascii')
            self.log.append(ln)
            if (ln.find("Insert MAC:") > -1):
                ser.write(bytes(self.eth_mac+'\r\n','ascii'))
            elif (ln.find("Insert IP:") > -1):
                ser.write(bytes(self.eth_ip+'\n','ascii'))
            elif (ln.find("Insert Mask:") > -1):
                ser.write(bytes(self.eth_mask+'\n','ascii'))
            elif (ln.find("Insert Gateway:") > -1):
                ser.write(bytes(self.eth_gateway+'\n','ascii'))
            elif (ln.find("Listening on port: 6791") > -1):
                self.eth_test()
            elif (ln.find("End of tests!") > -1):
                break
        return self.parse_results()

    def LED_parse(self):
        ind = [i for i, elem in enumerate(self.log) if '[LED]' in elem]
        self.test_results['led'] = OrderedDict()
        for i in ind:
            regex = re.findall(r"\d*\.?\d+", self.log[i])
            if len(regex) > 0:
                self.test_results['led'][regex[0]] = {'value':float(regex[1])}
                self.test_results['led'][regex[0]]['result'] = (1 if self.test_results['led'][regex[0]]['value'] < self.test_mask['led']['mask'] else 0)
        #Set the general result to 1 if all the tests passed
        res = 1
        for k,v in self.test_results['led'].items():
            for k1,v1 in v.items():
                if (k1 == 'result'):
                    res &= v1
        self.test_results['led']['result'] = res

    def GPIOLoopback_parse(self):
        self.test_results['gpio'] = OrderedDict()
        ind = [i for i, elem in enumerate(self.log) if 'Loopback' in elem]
        result = []
        for t, i in enumerate(ind):
            loop_pair = re.findall(r"\[([^]]+)\]", self.log[i])
            loop_res = re.findall("(Pass|Fail)", self.log[i])
            if len(loop_pair) > 0:
                result.append([loop_pair, (1 if loop_res[0] == 'Pass' else 0)])
                self.test_results['gpio'][t] = {'pin1':loop_pair[0],'pin2':loop_pair[1],'result':(1 if loop_res[0] == 'Pass' else 0)}
        #Set the general result to 1 if all the tests passed
        res = 1
        for k,v in self.test_results['gpio'].items():
            for k1,v1 in v.items():
                if (k1 == 'result'):
                    res &= v1
        self.test_results['gpio']['result'] = res

    def PowerSupply_parse(self):
        ind = [i for i, elem in enumerate(self.log) if 'Power Supply' in elem]
        self.test_results['powerSupply'] = OrderedDict()
        for i in ind:
            regex = re.findall(r"\d*\.?\d+", self.log[i])
            if len(regex) > 0:
                self.test_results['powerSupply'][regex[0]] = {'value':float(regex[1])}
                low = self.test_mask['powerSupply'][regex[0]]['nominal'] - self.test_mask['powerSupply'][regex[0]]['tolerance']
                high = self.test_mask['powerSupply'][regex[0]]['nominal'] + self.test_mask['powerSupply'][regex[0]]['tolerance']
                self.test_results['powerSupply'][regex[0]]['result'] = (1 if (low <= float(regex[1]) <= high) else 0)
        #Set the general result to 1 if all the tests passed
        res = 1
        for k,v in self.test_results['powerSupply'].items():
            for k1,v1 in v.items():
                if (k1 == 'result'):
                    res &= v1
        self.test_results['powerSupply']['result'] = res

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
        self.test_results['feram'] = {'pattern': ''.join(rand), 'result': result[0]}

    def Ethernet_parse(self):
        self.test_results['ethernet'] = OrderedDict()
        ind = [i for i, elem in enumerate(self.log) if 'Received:' in elem]
        for i in ind:
            regex = re.findall(r'"(.*?)"', self.log[i])
            if len(regex) > 0:
                self.test_results['ethernet']['message'] = regex[0]
        self.test_results['ethernet']['result'] = 1 if self.test_results['ethernet']['message'] == self.test_mask['ethernet']['message'] else 0
        self.test_results['ethernet']['mac'] = ':'.join([self.eth_mac[i:i+2] for i in range(0, len(self.eth_mac), 2)])
        self.test_results['ethernet']['ip'] = self.eth_ip
        self.test_results['ethernet']['gateway'] = self.eth_gateway
        self.test_results['ethernet']['mask'] = self.eth_mask

    def parse_results(self):
        self.LED_parse()
        self.GPIOLoopback_parse()
        self.PowerSupply_parse()
        self.Ethernet_parse()
        self.FeRAM_parse()

        res = 1
        for k,v in self.test_results.items():
            if isinstance(v, dict):
                for k1,v1 in v.items():
                    if (k1 == 'result'):
                        res &= v1
        self.test_results['result'] = res
        return res

    def dump(self, path):
        dump_abs = os.path.abspath(os.path.expanduser(path))
        pathlib.Path(os.path.dirname(dump_abs)).mkdir(parents=True, exist_ok=True)
        with open(dump_abs, 'w') as dump_f:
            json.dump(self.test_results, dump_f, indent=4, ensure_ascii=True)

if __name__ == "__main__":
    uc = RFFEuC_Test(("10.0.18.111", "255.255.255.0", "10.0.18.1", "DE:AD:BE:EF:12:34"), "/dev/ttyUSB0", 'Henrique Silva', 'TST0001','UC0001')
    uc.run()

    #uc.dump('./test_report/results.json')

    #pp = pprint.PrettyPrinter(indent=4)
    #pp.pprint(uc.test_results)

    rep = RFFEuC_Report(uc.test_results, "0", "1")
    rep.generate('./test_report')
