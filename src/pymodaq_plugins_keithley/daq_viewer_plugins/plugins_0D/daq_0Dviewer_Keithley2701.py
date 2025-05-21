from pymodaq.control_modules.viewer_utility_classes import comon_parameters
from pymodaq_plugins_keithley import config
from pymodaq_plugins_keithley.hardware.keithley27XX.Keithley27XX_Viewer import DAQ_0DViewer_Keithley27XX
from pymodaq_plugins_keithley.hardware.keithley27XX.keithley2701_VISADriver import Keithley2701VISADriver as Keithley
from pymodaq.utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))


class DAQ_0DViewer_Keithley2701(DAQ_0DViewer_Keithley27XX):
    """ Keithley viewer class for Keithley 2701 Multimeter/Switch System.
    """
    model = "2701"
    resources_list = []

    # Read configuration file
    for instr in config["Keithley", model].keys():
        if "INSTRUMENT" in instr:
            resources_list += [config["Keithley", model, instr, "rsrc_name"]]
    logger.info("resources list = {}".format(resources_list))

    params = comon_parameters + [
        {'title': 'Resources', 'name': 'resources', 'type': 'list', 'limits': resources_list,
         'value': resources_list[0]},
        DAQ_0DViewer_Keithley27XX.params
    ]

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)

    def ini_detector(self, controller=None):
        """Detector communication initialization

        :param controller: Custom object of a PyMoDAQ plugin (Slave case). None if one actuator/detector by controller.
        :type controller: object

        :return: Initialization status, false if it failed otherwise True
        :rtype: bool
        """
        logger.info("Detector 0D initialized")

        if self.settings.child('controller_status').value() == "Slave":
            if controller is None:
                raise Exception('no controller has been defined externally while this detector is a slave one')
            else:
                self.controller = controller
        else:
            try:
                # Select the resource to connect with and load the dedicated configuration
                for instr in config["Keithley", self.model]:
                    if "INSTRUMENT" in instr:
                        if config["Keithley", self.model, instr, "rsrc_name"] == self.settings["resources"]:
                            self.rsrc_name = config["Keithley", self.model, instr, "rsrc_name"]
                            self.panel = config["Keithley", self.model, instr, "panel"].upper()
                            self.instr = instr
                            logger.info("Panel configuration 0D_viewer: {}".format(self.panel))
                assert self.rsrc_name is not None, "rsrc_name"
                assert self.panel is not None, "panel"
                self.controller = Keithley(self.rsrc_name)
            except AssertionError as err:
                logger.error("{}: {} did not match any configuration".format(type(err), str(err)))
            except Exception as e:
                raise Exception('No controller could be defined because an error occurred \
                while connecting to the instrument. Error: {}'.format(str(e)))

        # Keithley initialization & identification
        self.controller.init_hardware()
        txt = self.controller.get_idn()
        self.settings.child('Keithley_Params', 'ID').setValue(txt)

        # Initialize detector communication and set the default value (SCAN_LIST)
        if self.panel == 'FRONT':
            self.settings.child('Keithley_Params', 'rearpanel').visible = False
            value = self.settings.child('Keithley_Params', 'frontpanel', 'frontmode').value()
            self.controller.current_mode = value
            self.controller.set_mode(value)
        elif self.panel == 'REAR':
            self.settings.child('Keithley_Params', 'frontpanel').visible = False
            self.settings.child('Keithley_Params', 'frontpanel').value = 'REAR'
            self.controller.configuration_sequence()
            value = 'SCAN_' + self.settings.child('Keithley_Params', 'rearpanel', 'rearmode').value()
            self.channels_in_selected_mode = self.controller.set_mode(value)
            logger.info("Channels to plot : {}".format(self.channels_in_selected_mode))
        logger.info("DAQ_viewer command sent to keithley visa driver : {}".format(value))

        self.status.initialized = True
        self.status.controller = self.controller

        return self.status
