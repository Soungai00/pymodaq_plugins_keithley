import pyvisa as visa
from pymodaq.utils.logger import set_logger, get_module_name
logger = set_logger(get_module_name(__file__))


class Keithley2100VISADriver:
    """VISA class driver for the Keithley 2100 Multimeter/Switch System

    This class relies on pyvisa module to communicate with the instrument via VISA protocol.
    Please refer to the instrument reference manual available at:
    https://www.tek.com/en/manual/keithley-model-2100-6-1-2-digit-resolution-digital-multimeter-calibration-manual
    """
    def __init__(self, rsrc_name):
        """Initialize KeithleyVISADriver class

        :param rsrc_name: VISA Resource name
        :type rsrc_name: string
        """
        self._instr = None
        self.rsrc_name = rsrc_name

    def init_hardware(self):
        """Initialize the selected VISA resource
        
        :param pyvisa_backend: Expects a pyvisa backend identifier or a path to the visa backend dll (ref. to pyvisa)
        :type pyvisa_backend: string
        """
        rm = visa.highlevel.ResourceManager()
        self._instr = rm.open_resource(self.rsrc_name,
                                           write_termination="\n",
                                           )    
       

    def clear_buffer(self):
        self._instr.write("TRAC:CLE")

    def clear_buffer_off(self):
        self._instr.write("TRAC:CLE:AUTO OFF")

    def clear_buffer_on(self):
        self._instr.write("TRAC:CLE:AUTO ON")

    def close(self):
        self._instr.write("ROUT:OPEN:ALL")
        self._instr.close()

    def get_card(self):
        return self._instr.query("*OPT?")
    
    def get_error(self):
        return self._instr.query("SYST:ERR?")
    
    def get_idn(self):
        return self._instr.query("*IDN?")
    
    def init_cont_off(self):
        self._instr.write("INIT:CONT OFF")
        
    def init_cont_on(self):
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
        self._instr.write("*CLS")
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

    def user_command(self):
        command = input('Enter here a command you want to send directly to the Keithley [if None, press enter]: ')
        if command != '':
            if command[-1] == "?":
                logger.info(self._instr.query(command)) 
            else:
                self._instr.write(command)
            self.user_command()
        else:
            pass
