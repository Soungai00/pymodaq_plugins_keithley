import numpy as np
from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import Parameter
from pymodaq.utils.daq_utils import DataFromPlugins
from pymodaq_data import DataToExport
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq_plugins_keithley.hardware.keithley2601A.keithley2601A_VISADriver import Keithley2601AVISADriver as Keithley
from pymodaq_plugins_keithley import config
from pymodaq.utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))

class DAQ_0DViewer_Keithley2601A(DAQ_Viewer_base):
    """ Keithley viewer class for Keithley 2601A Sourcemeter.
    """
    model = "2601A"
    resources_list = []
    live = False

    # Read configuration file
    for instr in config["Keithley", model].keys():
        if "INSTRUMENT" in instr:
            resources_list += [f"TCPIP::{config["Keithley", model, instr, "IP"]}::{config["Keithley", model, instr, "port"]}::SOCKET"]
    logger.info("resources list = {}".format(resources_list))

    params = comon_parameters + [
        {'title': '2601A Resources', 'name': 'resources', 'type': 'list', 'limits': resources_list,
         'value': resources_list[0]},
        {'title': 'ID:', 'name': 'ID', 'type': 'str', 'value': '', 'readonly': True},
    ]

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)

    def ini_attributes(self):
        super().ini_attributes()
        self.controller: Keithley = None
        self.instr = ""
        self.live = False

    def instantiate_controller(self, controller):
        """Check the configuration and instantiate the controller according to the selected resource"""
        try:
            # Select the resource to connect with and load the dedicated configuration
            for instr in config["Keithley", self.model]:
                if "INSTRUMENT" in instr:
                    if config["Keithley", self.model, instr, "IP"] in self.settings["resources"]:
                        self.instr = instr
                        self.controller = Keithley()
        except AssertionError as err:
            logger.error("{}: {} did not match any configuration".format(type(err), str(err)))
        except Exception as e:
            raise Exception('No controller could be defined because an error occurred \
            while connecting to the instrument. Error: {}'.format(str(e)))

    def ini_detector(self, controller=None):
        """Detector communication initialization

        :param controller: Custom object of a PyMoDAQ plugin (Slave case). None if one actuator/detector by controller.
        :type controller: object

        :return: Initialization status, false if it failed otherwise True
        :rtype: bool
        """
        logger.info("Detector 0D initializing")
        if not self.is_master:
            if controller is None:
                raise Exception('no controller has been defined externally while this detector is a slave one')
            else:
                self.controller = controller
        else:
            self.instantiate_controller(controller)

            # Keithley initialization & identification
            self.controller.init_hardware(self.instr)
        txt = self.controller.get_idn()
        self.settings.child('ID').setValue(txt)

        self.status.initialized = True
        self.status.controller = self.controller
        return self.status

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings"""
        pass

    def grab_data(self, Naverage=1, **kwargs):
        """Start a grab from the detector

        :param Naverage: Number of hardware averaging (if hardware averaging is possible,
            self.hardware_averaging should be set to True in class preamble, and you should code this implementation)
        :type Naverage: int

        :param kwargs: others optionals arguments
        :type kwargs: dict
        """
        # ACQUISITION OF DATA
        data_measured = [np.array([self.controller.measure_current()])]
        dte = DataToExport(name='keithley2601A',
                           data=[DataFromPlugins(name="Sourcemeter",
                                                 data=data_measured,
                                                 dim='Data0D',
                                                 labels=["Current"],
                                                 ),
                                 ])
        self.dte_signal.emit(dte)

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        self.emit_status(ThreadCommand('Update_Status', ['Acquisition stopped']))
        return ''

    def close(self):
        """Terminate the communication protocol"""
        self.controller.reset()
        self.controller.close()
        logger.info("communication ended successfully")


if __name__ == '__main__':
    main(__file__)
