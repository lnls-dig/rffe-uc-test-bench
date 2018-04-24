from pylatex.package import Package
from pylatex import Document, Section, Subsection, Subsubsection, Command, Tabular, Center, MultiColumn, Alignat
from pylatex.utils import NoEscape, italic, bold
from datetime import datetime
import pathlib
import binascii
import os

class RFFEuC_Report(object):

    def __init__(self, test_results, date=datetime.today()):
        self.date = date
        self.doc = Document(default_filepath='./', page_numbers=False)
        self.test_results = test_results

    def header(self):
        #Title
        self.doc.preamble.append(Command('title', 'RFFEuC Test Report'))
        self.doc.preamble.append(Command('date', NoEscape(r'')))
        self.doc.append(NoEscape(r'\maketitle'))

        with self.doc.create(Section('', numbering=False)):
            self.doc.append(bold('Board information:\n'))
            with self.doc.create(Center()) as centered:
                with centered.create(Tabular('|l|l|',row_height=1.2)) as tbl:
                    tbl.add_hline()
                    tbl.add_row(bold('Operator'), self.test_results['operator'])
                    tbl.add_hline()
                    tbl.add_row(bold('Board PN/SN'), ':'.join([self.test_results['boardPN'],self.test_results['boardSN']]))
                    tbl.add_hline()
                    tbl.add_row(bold('Testboard PN/SN'), ':'.join([self.test_results['testBoardPN'],self.test_results['testBoardSN']]))
                    tbl.add_hline()
                    tbl.add_row(bold('TestSW commit'), self.test_results['testSWCommit'])
                    tbl.add_hline()
                    tbl.add_row(bold('IP'), self.test_results['ethernet']['ip'])
                    tbl.add_hline()
                    tbl.add_row(bold('MAC'), self.test_results['ethernet']['mac'])
                    tbl.add_hline()
                    tbl.add_row(bold('Date'), self.test_results['date'])
                    tbl.add_hline()

            self.doc.append(bold('Test Results:\n'))
            with self.doc.create(Center()) as centered:
                with centered.create(Tabular('|l|c|',row_height=1.2)) as tbl:
                    tbl.add_hline()
                    tbl.add_row(bold('LED'), ('Pass' if self.test_results['led']['result'] else 'Fail'), color=('green' if self.test_results['led']['result'] else 'red'))
                    tbl.add_hline()
                    tbl.add_row(bold('GPIO Loopback'), ('Pass' if self.test_results['gpio']['result'] else 'Fail'), color=('green' if self.test_results['gpio']['result'] else 'red'))
                    tbl.add_hline()
                    tbl.add_row(bold('Power Supply'), ('Pass' if self.test_results['powerSupply']['result'] else 'Fail'), color=('green' if self.test_results['powerSupply']['result'] else 'red'))
                    tbl.add_hline()
                    tbl.add_row(bold('FeRAM'), ('Pass' if self.test_results['feram']['result'] else 'Fail'), color=('green' if self.test_results['feram']['result'] else 'red'))
                    tbl.add_hline()
                    tbl.add_row(bold('Ethernet'), ('Pass' if self.test_results['ethernet']['result'] else 'Fail'), color=('green' if self.test_results['ethernet']['result'] else 'red'))
                    tbl.add_hline()

    def LED_report(self):
        self.doc.append(NoEscape(r'\clearpage'))
        with self.doc.create(Section('LEDs')):
            with self.doc.create(Subsection('Description')):
                self.doc.append('This test asserts the correct assembly of the 4 LEDs on RFFEuC\'s edge.\n')
                self.doc.append('A large LDR (20mm) is positioned in front of all LEDs and is connected to one of the Analogic-to-Digital converter ports - routed through the TestBoard Jn connector.\n')
                self.doc.append('Each LED is activated separately and the LDR voltage is read and compared to a predefined mask.\n')

            with self.doc.create(Subsection('Results')):
                with self.doc.create(Center()) as centered:
                    with centered.create(Tabular('|c|c|c|',row_height=1.2)) as tbl:
                        tbl.add_hline()
                        tbl.add_row(bold('LED'), bold('LDR read [V]'), bold('Result'))
                        tbl.add_hline()
                        for key,val in self.test_results['led'].items():
                            if isinstance(val, dict):
                                tbl.add_row(bold(key), (val['value']), ('Pass' if val['result'] else 'Fail'), color=('green' if val['result'] else 'red'))
                                tbl.add_hline()

    def GPIOLoopback_report(self):
        self.doc.append(NoEscape(r'\clearpage'))
        with self.doc.create(Section('GPIO Loopback')):
            with self.doc.create(Subsection('Description')):
                self.doc.append('This test asserts the correct assembly of the GPIO pins on both RFFEuC\'s headers.')
                self.doc.append('In the TestBoard all GPIO pins are connected in pairs via a 1K1 resistor, so they\'re logically binded.\n')
                self.doc.append('Each pin in the loopback pair is tested as an Input and Output, changing the logic level of its pair to assert the electrical connection.\n')

            with self.doc.create(Subsection('Results')):
                with self.doc.create(Center()) as centered:
                    with centered.create(Tabular('|c|c|c|',row_height=1.2)) as tbl:
                        tbl.add_hline()
                        tbl.add_row((MultiColumn(2, align='|c|', data=bold('Loopback Pair')), bold('Result')))
                        tbl.add_hline()
                        for key,val in self.test_results['gpio'].items():
                            if isinstance(val, dict):
                                tbl.add_row(val['pin1'], val['pin2'], ('Pass' if val['result'] else 'Fail'), color=('green' if val['result'] else 'red'))
                                tbl.add_hline()

    def PowerSupply_report(self):
        self.doc.append(NoEscape(r'\clearpage'))
        with self.doc.create(Section('Power Supply')):
            with self.doc.create(Subsection('Description')):
                self.doc.append('This test asserts the correct assembly of the Voltage regulation circuit.\n')
                self.doc.append('Both power supply lines (5V and 3.3V) are tested using a simple voltage divider circuit present on the TestBoard. Given that the voltage divider provides a half of the real value to the RFFEuC ADC circuit, the following convertion is applied: \n')
                with self.doc.create(Alignat(numbering=False, escape=False)) as agn:
                    agn.append(r'V_{PS} = ADC_{read} * 3.3 * 2 \\')

            with self.doc.create(Subsection('Results')):
                with self.doc.create(Center()) as centered:
                    with centered.create(Tabular('|c|c|c|',row_height=1.2)) as tbl:
                        tbl.add_hline()
                        tbl.add_row(bold('Power Supply'), bold('Measured [V]'), bold('Result') )
                        tbl.add_hline()
                        for key,val in self.test_results['powerSupply'].items():
                            if isinstance(val, dict):
                                tbl.add_row(bold(key+'V'), val['value'] ,('Pass' if val['result'] else 'Fail'), color=('green' if val['result'] else 'red'))
                                tbl.add_hline()

    def FERAM_report(self):
        self.doc.append(NoEscape(r'\clearpage'))
        with self.doc.create(Section('FeRAM')):
            with self.doc.create(Subsection('Description')):
                self.doc.append('This test asserts the correct assembly of the FeRAM chip (IC1 - FM24CL16B-G) and its communication lines (I2C).\n')
                self.doc.append('A random pattern, 256 bytes long, is generated by reading the two least significant bits of ADC0 and shifting them left. This pattern is then written in each page of the FeRAM and then read back to be compared with the original data.\n')

            with self.doc.create(Subsection('Results')):
                with self.doc.create(Center()) as centered:
                    with centered.create(Tabular('|c|',row_height=0.9)) as tbl:
                        tbl.add_hline()
                        tbl.add_row((bold('Random Pattern'),))
                        tbl.add_hline()
                        result_str = [ ''.join(self.test_results['feram']['pattern'][i:i+16]) for i in range(0, len(self.test_results['feram']['pattern']), 16) ]
                        for item in result_str:
                            tbl.add_row(((item),))
                        tbl.add_hline()

                with self.doc.create(Center()) as centered:
                    with centered.create(Tabular('|c|',row_height=1.0)) as tbl:
                        tbl.add_hline()
                        tbl.add_row((bold('Result'),))
                        tbl.add_hline()
                        tbl.add_row((('Pass' if self.test_results['feram']['result'] else 'Fail'),), color=('green' if self.test_results['feram']['result'] else 'red') )
                        tbl.add_hline()

    def Ethernet_report(self):
        hex_str = str(binascii.hexlify(self.test_results['ethernet']['message'].encode('ascii')),'ascii')
        ascii_str = self.test_results['ethernet']['message']

        self.doc.append(NoEscape(r'\clearpage'))
        with self.doc.create(Section('Ethernet')):
            with self.doc.create(Subsection('Description')):
                self.doc.append('This test asserts the correct assembly of all the Ethernet related circuit, including the PLL (CDCE906) used to generate the 50MHz reference, the PHY chip and the RJ45 connector.\n')

                with self.doc.create(Subsubsection('PLL Configuration')):
                    self.doc.append('At first the PLL is configured to generate 50MHz in its output using a 12MHz oscillator. The output frequency can be calculated using the following equation:\n')
                    with self.doc.create(Alignat(numbering=False, escape=False)) as agn:
                        agn.append(r'f_{out} = \frac{3 * N * f_{in}}{M*P} \\')
                    self.doc.append(NoEscape(r'To generate 50MHz, the following values are used in the PLL configuration: $ f_{in} = 12MHz$, $M = 9$, $N = 25$ , $P = 2$'))

                with self.doc.create(Subsubsection('TCP Server')):
                    self.doc.append(NoEscape(r'The RFFEuC will establish an Ethernet connection using the PHY interface chip and, if successfull, will create a TCP Server and listen on port 6791 for incoming connections. In order for the test to pass, an external client must connect to this port and send the following string: \textbf{\lq\lq Test msg!\rq\rq}, including a string terminating char (0x00) at the end.'))

            with self.doc.create(Subsection('Results')):
                with self.doc.create(Center()) as centered:
                    with centered.create(Tabular('|c|c|c|c|',row_height=1.2)) as tbl:
                        tbl.add_hline()
                        tbl.add_row(bold('MAC'), bold('IP'), bold('Gateway'), bold('Mask') )
                        tbl.add_hline()
                        tbl.add_row(self.test_results['ethernet']['mac'], self.test_results['ethernet']['ip'], self.test_results['ethernet']['gateway'], self.test_results['ethernet']['mask'])
                        tbl.add_hline()

                with self.doc.create(Center()) as centered:
                    with centered.create(Tabular('|c|c|c|',row_height=1.2)) as tbl:
                        tbl.add_hline()
                        tbl.add_row(bold('Received String'), bold('Hexadecimal'), bold('Result') )
                        tbl.add_hline()
                        tbl.add_row(ascii_str, hex_str, ('Pass' if self.test_results['ethernet']['result'] else 'Fail'), color=('green' if self.test_results['ethernet']['result'] else 'red'))
                        tbl.add_hline()

    def generate(self, file_dir='./reports/', file_name='report1'):
        self.header()
        self.LED_report()
        self.GPIOLoopback_report()
        self.PowerSupply_report()
        self.FERAM_report()
        self.Ethernet_report()

        file_dir_abs = os.path.abspath(os.path.expanduser(file_dir))
        if file_name.lower().endswith('.pdf'):
            raise NameError('File name must not have an extension!')
        pathlib.Path(file_dir_abs).mkdir(parents=True, exist_ok=True)

        report_full_name = file_dir_abs+'/'+file_name
        print('Saving report to '+report_full_name+'.pdf')

        self.doc.generate_pdf(report_full_name)
