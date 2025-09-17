import numpy as np
import pyvisa as visa
from pymodaq_plugins_keithley import config
from pymodaq.utils.logger import set_logger, get_module_name
logger = set_logger(get_module_name(__file__))

class Keithley2601AVISADriver:
    """Driver class for keithley 2601A SourceMeter"""

    source_mode = "current"
    source_current = 0
    source_current_range = 10e-3
    compliance_voltage = 10
    source_voltage = 0
    source_voltage_range = 10e-3
    compliance_current = 10

    def __init__(self):
        self.ip_addr = ""
        self.port = ""
        self.visa_addr = ""
        self._instr = None

    def init_hardware(self, instr):
        """Initialize the selected resource"""
        self.ip_addr = config["Keithley", "2601A", instr, "IP"]
        self.port = config["Keithley", "2601A", instr, "port"]
        self.visa_addr = f"TCPIP::{self.ip_addr}::{self.port}::SOCKET"
        # Open connexion with instrument
        rm = visa.highlevel.ResourceManager('@py')
        logger.info("Resources detected by pyvisa: {}".format(rm.list_resources(query='?*')))
        try:
            self._instr = rm.open_resource(self.visa_addr,
                                           write_termination="\n",
                                           read_termination="\n")
            self._instr.timeout = 10000
        except:
            print("Init hardware failed")

    def get_idn(self):
        # Query identification
        return self._instr.query("*IDN?")

    def reset(self):
        # Clear measurement event register
        self._instr.write("*CLS")
        # Reset to defaults settings
        self._instr.write("*RST")

    def auto_range_source(self):
        """Configure the source to us an automatic range."""
        if self.source_mode == "current":
            self._instr.write("smua.source.autorangei = smua.AUTORANGE_ON")
        else:
            self._instr.write("smua.source.autorangev = smua.AUTORANGE_ON")

    def configuration_sequence(self):
        self._instr.write("*RST")
        #self._instr.write("format.data = format.ASCII")
        #self._instr.write("format.asciiprecision = 6")

        self.source_configuration()
        self.measure_configuration()
        self._instr.write(f"smua.source.levelv = {float(0)}")
        self.enable_source()

    def source_configuration(self):
        self._instr.write("smua.source.func = smua.OUTPUT_DCVOLTS")
        self._instr.write("smua.source.limiti = 0.5")
        self._instr.write("smua.source.autorangev = smua.AUTORANGE_ON")

    def measure_configuration(self):
        self._instr.write("smua.measure.rangei = 0.5")
        self._instr.write("smua.measure.autorangei = smua.AUTORANGE_ON")

    def enable_source(self):
        self._instr.write("smua.source.output = smua.OUTPUT_ON")

    def disable_source(self):
        self._instr.write("smua.source.output = smua.OUTPUT_OFF")

    def measure_current(self):
        """Make 1 measurement of I"""
        return float(self._instr.query("print(smua.measure.i())"))

    def measure_voltage(self):
        """Make 1 measurement of V"""
        return float(self._instr.query("print(smua.measure.v())"))

    def apply_current(self, current_range=None, compliance_voltage=0.1):
        """Configure the instrument to apply a source current, and
        uses an auto range unless a current range is specified.
        The compliance voltage is also set.

        :param compliance_voltage: A float in the correct range for a
                                   :attr:'~.Keithley2601A.compliance_voltage'
        :param current_range: A :attr:'~.Keithley2601A.current_range' value or None
        """
        self.source_mode = "current"
        if current_range is None:
            self._instr.write("smua.measure.autorangei = smua.AUTORANGE_ON")
        else:
            self.source_current_range = current_range
        self.compliance_voltage = compliance_voltage
        self.check_errors()

    def apply_voltage(self, voltage_range=None, compliance_current=10):
        """Configure the instrument to apply a source voltage, and
        uses an auto range unless a voltage range is specified.
        The compliance current is also set.

        :param compliance_current: A float in the correct range for a
                                   :attr:'~.Keithley2601A.compliance_current'
        :param voltage_range: A :attr:'~.Keithley2601A.voltage_range' value or None
        """
        self.source_mode = "voltage"
        if voltage_range is None:
            self._instr.write("smua.measure.autorangev = smua.AUTORANGE_ON")
        else:
            self.source_voltage_range = voltage_range
        self.compliance_current = compliance_current
        self.check_errors()

    def modify_current(self, current):
        self._instr.write(f"smua.source.leveli = {float(current)}")

    def modify_voltage(self, voltage):
        self._instr.write(f"smua.source.levelv = {float(voltage)}")

    def wait_complete(self):
        self._instr.write("waitcomplete()")

    def close(self):
        self.disable_source()
        self._instr.close()

    def check_errors(self):
        """Read the oldest entry from the error queue and removes it from the queue"""
        return self._instr.query("print(errorqueue.next())")

if __name__ == '__main__':
    try:
        k2601A = Keithley2601AVISADriver()
        k2601A.init_hardware()
        print(k2601A.get_idn())
        k2601A.configuration_sequence()
        currents = []
        voltage = np.arange(23)
        for v in voltage:
            k2601A._instr.write(f"smua.source.levelv = {float(v)}")
            currents.append(k2601A._instr.query("print(smua.measure.i())"))
            k2601A._instr.write("waitcomplete()")
        print(currents)
    except Exception as e:
        print(str(e))
    finally:
        k2601A.close()