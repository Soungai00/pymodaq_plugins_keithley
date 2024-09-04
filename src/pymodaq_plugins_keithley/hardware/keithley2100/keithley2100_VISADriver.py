# hardware controller for Keithley 2100

import pyvisa as visa 


class Keithley2100VISADriver: 

   def __init__(self, rsrc_name, pyvisa_backend='@ni'):
        """
        Parameters
        ----------
        rsrc_name   (string)        VISA Resource name
        pyvisa_backend  (string)    Expects a pyvisa backend identifier or a path to the visa backend dll (ref. to pyvisa)
        """
        rm = visa.highlevel.ResourceManager(pyvisa_backend)
        self._instr = rm.open_resource(rsrc_name)

        self._instr.read_termination = '\n'
        self._instr.write_termination = '\n'
