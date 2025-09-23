import numpy as np
from typing import Union, List, Dict
from pymodaq_plugins_keithley import config
from pymodaq.control_modules.move_utility_classes import main, DAQ_Move_base, comon_parameters_fun, DataActuatorType,\
    DataActuator  # common set of parameters for all actuators
from pymodaq_gui.parameter.utils import Parameter, iter_children
from pymodaq_utils.utils import ThreadCommand, getLineInfo # object used to send info back to the main thread
from pymodaq_plugins_keithley.hardware.keithley2601A.keithley2601A_VISADriver import Keithley2601AVISADriver as Keithley
from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))

SOURCE_MODES = ['Current', 'Voltage']
EPSILON_CURRENT = 1e-5
EPSILON_VOLTAGE = 1e-3


class DAQ_Move_Keithley2601A(DAQ_Move_base):
    """ Keithley move class for Keithley 2601A Sourcemeter.
    """
    model = "2601A"
    resources_list = []
    live = False

    is_multiaxes = False
    _axis_names: Union[List[str], Dict[str, str]] = ['Voltage']
    _controller_units: Union[str, List[str]] = ['V']
    _epsilon: Union[float, List[float]] = [1e-4]

    data_actuator_type = DataActuatorType.DataActuator

    # Read configuration file
    for instr in config["Keithley", model].keys():
        if "INSTRUMENT" in instr:
            resources_list += [f"TCPIP::{config['Keithley', model, instr, 'IP']}::{config['Keithley', model, instr, 'port']}::SOCKET"]
    logger.info("resources list = {}".format(resources_list))

    params = comon_parameters_fun(is_multiaxes=is_multiaxes, axis_names=_axis_names, epsilon=_epsilon) + [
        {'title': '2601A Resources', 'name': 'resources', 'type': 'list', 'limits': resources_list,
         'value': resources_list[0]},
        {'title': 'ID:', 'name': 'ID', 'type': 'str', 'value': '', 'readonly': True},
        {'title': 'Source Mode:', 'name': 'source_mode', 'type': 'list', 'limits': SOURCE_MODES},
        {'title': 'Enabled:', 'name': 'enabled', 'type': 'led_push', 'value': False},
        {'title': 'Current Mode:', 'name': 'current_mode', 'type': 'group', 'children': [
            {'title': 'Current Range:', 'name': 'current_range', 'type': 'float', 'value': 10e-3, 'min': 0.},
            {'title': 'Compliance Voltage:', 'name': 'voltage_compliance', 'type': 'float',
             'value': 10, 'min': 0.}]},
        {'title': 'Voltage Mode:', 'name': 'voltage_mode', 'type': 'group', 'visible': True, 'children': [
         {'title': 'Voltage Range:', 'name': 'voltage_range', 'type': 'float', 'value': 10, 'min': 0.,
          'max': 210.},
         {'title': 'Compliance Current:', 'name': 'current_compliance', 'type': 'float',
          'value': 5e-1, 'min': 0.}]},
        ]

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)

    def ini_attributes(self):
        super().ini_attributes()
        self.controller: Keithley = None
        self.instr = ""
        self._enabled = False
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

    def ini_stage(self, controller=None):
        """Actuator communication initialization

        :param controller: Custom object of a PyMoDAQ plugin (Slave case). None if one actuator/detector by controller.
        :type controller: object

        :return: Initialization status, false if it failed otherwise True
        :rtype: bool
        """
        logger.info("Actuator 0D initializing")
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
        self.settings.child("source_mode").setValue("Voltage")
        self.enable_source(True)

        self.status.initialized = True
        self.status.controller = self.controller
        return self.status

    def commit_settings(self, param):
        if param.name() == "source_mode" or \
            param.name() in iter_children(self.settings.child('current_mode'), []) or \
                param.name() in iter_children(self.settings.child('voltage_mode'), []):

            if self.enabled:  # if was enabled, disabled it
                self.enable_source(False)
            self.set_source(param.value(), *self.get_range_compliance())
            if param.name() == "source_mode":
                self.settings.child('current_mode').show(param.value() == 'Current')
                self.settings.child('voltage_mode').show(param.value() != 'Current')
                if param.value() == 'Current':
                    self.controller.source_current = 0
                    self.controller.measure_voltage()
                else:
                    self.controller.source_voltage = 0.
                    self.controller.measure_current()

        elif param.name() == 'enabled':
            self.enable_source(param.value())

    def get_actuator_value(self):
        """Get the current position from the hardware with scaling conversion.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """
        if self.enabled:
            if self.settings.child('source_mode').value() == 'Current':
                pos = self.controller.measure_current()
            else:
                pos = self.controller.measure_voltage()
            if isinstance(pos, list):
                logger.debug(f"Got multiple return values for {self.settings.child('source_mode').value()}"
                             f": {pos}")
                pos = pos[0]
        else:
            pos = 0.
        pos = DataActuator(data=pos)
        pos = self.get_position_with_scaling(pos)
        self.current_position = pos

        self.emit_status(ThreadCommand('get_actuator_value', [pos]))
        return pos

    @property
    def enabled(self):
        return self._enabled

    def enable_source(self, enable=True):
        self._enabled = enable
        if enable:
            self.controller.enable_source()
        else:
            self.controller.disable_source()
        self.settings.child('enabled').setValue(enable)

    def set_source(self, source_mode='Current', range=None, compliance=None):
        if source_mode == 'Current':
            if compliance is None:
                compliance = 0.1
            self.controller.apply_current(current_range=range, compliance_voltage=compliance)
            self.settings.child('epsilon').setValue(EPSILON_CURRENT)
        else:
            if compliance is None:
                compliance = 10
            self.controller.apply_voltage(voltage_range=range, compliance_current=compliance)
            self.settings.child('epsilon').setValue(EPSILON_VOLTAGE)

    def get_range_compliance(self):
        if self.settings.child('source_mode').value() == 'Current':
            range = self.settings.child('current_mode', 'current_range').value()
            compliance = self.settings.child('current_mode', 'voltage_compliance').value()
        else:
            range = self.settings.child('voltage_mode', 'voltage_range').value()
            compliance = self.settings.child('voltage_mode', 'current_compliance').value()
        return range, compliance

    def move_Abs(self, position):
        position = self.check_bound(position)  #if user checked bounds, the defined bounds are applied here
        position = self.set_position_with_scaling(position)  # apply scaling if the user specified one
        if self.settings.child('source_mode').value() == 'Current':
            self.controller.source_current = position
        else:
            self.controller.source_voltage = position

        if self.enabled:
            if self.settings.child('source_mode').value() == 'Current':
                self.controller.modify_current(position.value())
                self.controller.wait_complete()
                pos = self.controller.measure_voltage()
            else:
                self.controller.modify_voltage(position.value())
                self.controller.wait_complete()
                pos = self.controller.measure_current()


        self.target_position = position
        self.current_position = self.target_position #bypass checking

    def move_Rel(self, position):
        position = self.check_bound(self.current_position+position)-self.current_position
        self.target_position = position + self.current_position
        self.move_Abs(self.target_position)

    def move_Home(self):
        self.move_Abs(DataActuator(data=0))

    def stop_motion(self):
        self.move_done()  # to let the interface know the actuator stopped

    def close(self):
        """End communication with instrument"""
        if self.is_master:
            self.controller.close()
            logger.info("communication ended successfully")

if __name__ == '__main__':
    main(__file__)