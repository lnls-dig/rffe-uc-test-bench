import serial
import subprocess
from subprocess import CalledProcessError
import os

class LPCProg(object):

    def __init__(self, serial_port, bin_path='./lpc21isp', baud_rate=230400, osc_rate=12000):
        self.serial_port = serial_port
        self.osc_rate = osc_rate
        self.bin_path = bin_path
        if baud_rate <= 230400:
            self.baud_rate = baud_rate
        else:
            raise ValueError('Baud rate must be lower than 230400!')

    def program(self, filename, wipe=True, verify=True, debug=False):
        flags = [self.bin_path, '-control']
        extension = os.path.splitext(filename)[1]

        flags.extend([('-debug5' if debug else '-debug0')])
        if wipe:
            flags.extend(['-wipe'])
        if verify:
            flags.extend(['-verify'])

        #'filename' is a positional argument, so it must be added here after all optional arguments!!
        if extension == '.bin':
            flags.extend(['-bin',filename])
        elif extension == '.hex':
            flags.extend(['-hex',filename])
        else:
            raise TypeError('File must be binary or hexadecimal!')

        flags.extend([self.serial_port, str(self.baud_rate), str(self.osc_rate)])

        try:
            output = subprocess.run(flags)
        except CalledProcessError:
            raise

        if output.returncode != 10:
            raise RuntimeError('LPC Programming failed with error: '+str(output.returncode))

        return 1
