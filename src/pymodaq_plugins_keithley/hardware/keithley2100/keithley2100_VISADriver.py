import numpy as np
import pyvisa as visa
from pymodaq_plugins_keithley import config
from pymodaq.utils.logger import set_logger, get_module_name
logger = set_logger(get_module_name(__file__))

print("In keithley2100_VISADriver.py")
class Keithley2100VISADriver:
    """VISA class driver for the Keithley 2100 Multimeter/Switch System

    This class relies on pyvisa module to communicate with the instrument via VISA protocol.
    Please refer to the instrument reference manual available at:
    https://www.tek.com/en/manual/keithley-model-2100-6-1-2-digit-resolution-digital-multimeter-calibration-manual
    """
    # List the Keithley instruments the user has configured from the .toml configuration file
    list_instruments = {}
    # for instr in config["Keithley", "2100"].keys():
    #     if "INSTRUMENT" in instr:
    #         list_instruments[instr] = config["Keithley", "2100", instr, "rsrc_name"]
    logger.info("Configured instruments: {}".format(list(list_instruments.items())))

    def __init__(self, rsrc_name):
        """Initialize KeithleyVISADriver class

        :param rsrc_name: VISA Resource name
        :type rsrc_name: string
        """
        self._instr = None
        self.rsrc_name = rsrc_name
        self.instr = ""
        self.configured_modules = {}

    def init_hardware(self):
        """Initialize the selected VISA resource
        
        :param pyvisa_backend: Expects a pyvisa backend identifier or a path to the visa backend dll (ref. to pyvisa)
        :type pyvisa_backend: string
        """
        # Open connexion with instrument
        print(f"self.rsrc_name = {self.rsrc_name} in hardware code")
        rm = visa.highlevel.ResourceManager()
        self._instr = rm.open_resource(self.rsrc_name,
                                           write_termination="\n",
                                        #    read_termination="\n",
                                           )        # logger.info("Resources detected by pyvisa: {}".format(rm.list_resources(query='?*')))
        # try:
        #     self._instr = rm.open_resource(self.rsrc_name,
        #                                    write_termination="\n",
        #                                 #    read_termination="\n",
        #                                    )
        #     self._instr.timeout = 10000

        #     model = self.get_idn()[32:36]
        #     if "21" not in model:
        #         logger.warning("Driver designed to use Keithley 2100, not {} model. Problems may occur.".format(model))
        #     for instr in config["Keithley", "2100"]:
        #         if type(config["Keithley", "2100", instr]) == dict:
        #             if self.rsrc_name in config["Keithley", "2100", instr, "rsrc_name"]:
        #                 self.instr = instr
        #     logger.info("Instrument selected: {} ".format(config["Keithley", "2100", self.instr, "rsrc_name"]))
        #     logger.info("Keithley model : {}".format(config["Keithley", "2100", self.instr, "model_name"]))
        # except visa.errors.VisaIOError as err:
        #     logger.error(err)


    def clear_buffer(self):
        # Default: auto clear when scan start
        self._instr.write("TRAC:CLE")

    def clear_buffer_off(self):
        # Disable buffer auto clear
        self._instr.write("TRAC:CLE:AUTO OFF")

    def clear_buffer_on(self):
        # Disable buffer auto clear
        self._instr.write("TRAC:CLE:AUTO ON")

    def close(self):
        self._instr.write("ROUT:OPEN:ALL")
        self._instr.close()

    def data(self):
        # """Get data from instrument
        # """
        # return float(self._instr.query(":READ?"))

        # FIXME: this was just restored from daq_0Dviewer_Keithley27xx.py. If this does now work, use return float(self._instr.query(":READ?")) as above.
        """Get data from instrument

        Make the Keithley perform 3 actions: init, trigger, fetch. Then process the answer to return 3 variables:
        - The answer (string)
        - The measurement values (numpy array)
        - The timestamp of each measurement (numpy array)
        """
        if not self.sample_count_1:
            # Initiate scan
            self._instr.write("INIT")
            # Trigger scan
            self._instr.write("*TRG")
            # Get data (equivalent to TRAC:DATA? from buffer)
            str_answer = self._instr.query("FETCH?")
        else:
            str_answer = self._instr.query("FETCH?")
        # Split the instrument answer (MEASUREMENT,TIME,READING COUNT) to create a list
        list_split_answer = str_answer.split(",")

        # MEASUREMENT & TIME EXTRACTION
        list_measurements = list_split_answer[::3]
        str_measurements = ''
        list_times = list_split_answer[1::3]
        str_times = ''
        for j in range(len(list_measurements)):
            if not j == 0:
                str_measurements += ','
                str_times += ','
            for l1 in range(len(list_measurements[j])):
                test_carac = list_measurements[j][-(l1+1)]
                # Remove non-digit characters (units)
                if test_carac.isdigit():
                    if l1 == 0:
                        str_measurements += list_measurements[j]
                    else:
                        str_measurements += list_measurements[j][:-l1]
                    break
            for l2 in range(len(list_times[j])):
                test_carac = list_times[j][-(l2+1)]
                # Remove non-digit characters (units)
                if test_carac.isdigit():
                    if l2 == 0:
                        str_times += list_times[j]
                    else:
                        str_times += list_times[j][:-l2]
                    break

        # Split created string to access each value
        list_measurements_values = str_measurements.split(",")
        list_times_values = str_times.split(",")
        # Create numpy.array containing desired values (float type)
        array_measurements_values = np.array(list_measurements_values, dtype=float)
        if not self.sample_count_1:
            array_times_values = np.array(list_times_values, dtype=float)
        else:
            array_times_values = np.array([0], dtype=float)

        return str_answer, array_measurements_values, array_times_values

    def get_card(self):
        # Query switching module
        return self._instr.query("*OPT?")
    
    def get_error(self):
        # Ask the keithley to return the last current error
        return self._instr.query("SYST:ERR?")
    
    def get_idn(self):
        # Query identification
        return self._instr.query("*IDN?")
    
    def init_cont_off(self):
        # Disable continuous initiation
        self._instr.write("INIT:CONT OFF")
        
    def init_cont_on(self):
        # Enable continuous initiation
        self._instr.write("INIT:CONT ON")

    def mode_temp_frtd(self, channel, transducer, frtd_type,):
        self._instr.write("TEMP:TRAN " + transducer + "," + channel)
        self._instr.write("TEMP:FRTD:TYPE " + frtd_type + "," + channel)

    def mode_temp_tc(self, channel, transducer, tc_type, ref_junc,):
        self._instr.write("TEMP:TRAN " + transducer + "," + channel)
        self._instr.write("TEMP:TC:TYPE " + tc_type + "," + channel)
        self._instr.write("TEMP:RJUN:RSEL " + ref_junc + "," + channel)

    def mode_temp_ther(self, channel, transducer, ther_type,):
        self._instr.write("TEMP:TRAN " + transducer + "," + channel)
        self._instr.write("TEMP:THER:TYPE " + ther_type + "," + channel)
    
    def reset(self):
        # Clear measurement event register
        self._instr.write("*CLS")
        # One-shot measurement mode (Equivalent to INIT:COUNT OFF)
        self._instr.write("*RST")

    def read(self):
        return float(self._instr.query("READ?"))

    def set_mode(self, mode, **kwargs):
        """

        Parameters
        ----------
        mode    (string)    Measurement configuration ('VDC', 'VAC', 'IDC', 'IAC', 'R2W' and 'R4W' modes are supported)
        kwargs  (dict)      Used to pass optional arguments ('range' and 'resolution' are the only supported keys)

        Returns
        -------

        """
        assert (isinstance(mode, str))
        mode = mode.lower()

        cmd = ':CONF:'

        if mode == "Ohm2".lower() or mode == "R2W".lower():
            cmd += "RES"
        elif mode == "Ohm4".lower() or mode == "R4W".lower():
            cmd += "FRES"
        elif mode == "VDC".lower() or mode == "V".lower():
            cmd += "VOLT:DC"
        elif mode == "VAC".lower():
            cmd += "VOLT:AC"
        elif mode == "IDC".lower() or mode == "I".lower():
            cmd += "CURR:DC"
        elif mode == "IAC".lower():
            cmd += "CURR:AC"

        if 'range' in kwargs.keys():
            cmd += ' ' + str(kwargs['range'])
            if 'resolution' in kwargs.keys():
                cmd += ',' + str(kwargs['resolution'])
        elif 'resolution' in kwargs.keys():
            cmd += ' DEF,' + str(kwargs['resolution'])

        self._instr.write(cmd)

    # def stop_acquisition(self):
    #     # If scan in process, stop it
    #     self._instr.write("ROUT:SCAN:LSEL NONE")

    def user_command(self):
        command = input('Enter here a command you want to send directly to the Keithley [if None, press enter]: ')
        if command != '':
            if command[-1] == "?":
                print(self._instr.query(command))
            else:
                self._instr.write(command)
            self.user_command()
        else:
            pass


if __name__ == "__main__":
    try:
        print("In main")

        # You can use this main section for:
        # - Testing connexion and communication with your instrument
        # - Testing new methods in developer mode

        RM = visa.ResourceManager("@ivi")
        print("list resources", RM.list_resources())

        # K2100 Instance of KeithleyVISADriver class (replace ASRL1::INSTR by the name of your resource)
        k2100 = Keithley2100VISADriver("ASRL1::INSTR")
        k2100.init_hardware()
        print("IDN?")
        print(k2100.get_idn())
        k2100.reset()

        # Daq_viewer simulation first run
        k2100.set_mode(str(input('Enter which mode you want to scan \
        [scan_scan_list, scan_volt:dc, scan_r2w, scan_temp...]:')))
        print('Manual scan example of command set to send directly: >init >*trg >trac:data?')
        k2100.user_command()
        print('Automatic scan example with 2 iterations')
        for i in range(2):
            print(k2100.data())
        print(k2100.data())

        # Daq_viewer simulation change mode
        k2100.set_mode(str(input('Enter which mode you want to scan \
        [scan_scan_list, scan_volt:dc, scan_r2w, scan_temp...]:')))
        for i in range(2):
            print(k2100.data())
        print(k2100.data())

        k2100.clear_buffer()
        k2100.close()

        print("Out")

    except Exception as e:
        print("Exception ({}): {}".format(type(e), str(e)))
