import numpy as np
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataFromPlugins, DataToExport
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter
from pymodaq_plugins_keithley import config
from pymodaq_plugins_keithley.hardware.keithley2100.keithley2100_VISADriver import Keithley2100VISADriver as Keithley
from pymodaq.utils.logger import set_logger, get_module_name
logger = set_logger(get_module_name(__file__))

rsrc_name: str
instr: str
panel: str
channels_in_selected_mode: str
resources_list = []


class DAQ_0DViewer_Keithley2100(DAQ_Viewer_base):
    """ Keithley plugin class for a OD viewer.

    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Viewer module through inheritance via
    DAQ_Viewer_base. It makes a bridge between the DAQ_Viewer module and the keithley2100_VISADriver.

    :param controller: The particular object that allow the communication with the keithley2100_VISADriver.
    :type  controller:  object

    :param params: Parameters displayed in the daq_viewer interface
    :type params: dictionary list
    """

    
    # Read configuration file
    for instr in config["Keithley", "2100"].keys():
        if "INSTRUMENT" in instr:
            resources_list += [config["Keithley", "2100", instr, "rsrc_name"]]
    logger.info("resources list = {}" .format(resources_list))

    params = comon_parameters + [
        {'title': 'Resources', 'name': 'resources', 'type': 'list', 'limits': resources_list,
         'value': resources_list[0]},
        {'title': 'Keithley2100 Parameters', 'name': 'K2100Params', 'type': 'group', 'children': [
            {'title': 'ID', 'name': 'ID', 'type': 'text', 'value': ''},
            {'title': 'Mode', 'name': 'mode', 'type': 'list', 'limits': ['VDC', 'VAC', 'R2W', 'R4W'], 'value': 'VDC'},

        ]},
    ]

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)

    def ini_attributes(self):
        """Attributes init when DAQ_0DViewer_Keithley class is instanced"""
        self.controller: Keithley = None
        self.channels_in_selected_mode = None
        self.rsrc_name = None
        self.panel = None
        self.instr = None

    def commit_settings(self, param):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
       
        if param.name() == "mode":
           self.controller.set_mode()
           logger.info("mode changed to {}".format(param.value())) 

    def ini_detector(self, controller=None):
        """Detector communication initialization

        :param controller: Custom object of a PyMoDAQ plugin (Slave case). None if one actuator/detector by controller.
        :type controller: object

        :return: Initialization status, false if it failed otherwise True
        :rtype: bool
        """
        logger.info("Detector 0D initialized")

        if self.is_master: 
            self.controller = Keithley(self.rsrc_name)
            self.controller.init_hardware()
            txt = self.controller.get_idn()
            self.settings.child('K2100Params', 'ID').setValue(txt)
            self.controller.set_mode(self.settings.child('K2100Params', 'mode').value())
        else:
            logger.warning("No controller found")
            self.status.initialized = False
            return self.status 
        
        self.dte_signal_temp.emit(DataToExport(name = 'K2100', data = [DataFromPlugins(name = 'K2100_1', 
                                                data = [np.array([0]), np.array([0])], dim = 'Data0D', Labels = ['time', 'voltage'])]))

       
        self.status.initialized = True
        self.status.controller = self.controller

        return self.status

    def close(self):
        """Terminate the communication protocol"""
        self.controller.close()
        logger.info("communication ended successfully")

    def grab_data(self, Naverage=1, **kwargs):
        """
            | Start new acquisition.
            |
            |
            | Send the data_grabed_signal once done.

            =============== ======== ===============================================
            **Parameters**  **Type**  **Description**
            *Naverage*      int       specify the threshold of the mean calculation
            =============== ======== ===============================================

        """
        data = self.controller.read()
        dte = DataToExport(name='K2100',
                                        data=[DataFromPlugins(name='K2100', data=data,
                                                            dim='Data0D', labels=['dat0', 'data1'])])

        self.dte_signal.emit(dte)

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        self.emit_status(ThreadCommand('Update_Status', ['Acquisition stopped']))
        return ''

if __name__ == '__main__':
    main(__file__)
