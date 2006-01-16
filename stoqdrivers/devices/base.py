# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Stoqdrivers
## Copyright (C) 2006 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
## USA.
##
## Author(s): Henrique Romano             <henrique@async.com.br>
##
"""
stoqdrivers/devices/base.py:

    Generic base class implementation for all devices.
"""

import gettext

from kiwi.python import namedAny
import gobject

from stoqdrivers.log import Logger
from stoqdrivers.configparser import StoqdriversConfig
from stoqdrivers.exceptions import CriticalError, ConfigError
from stoqdrivers.constants import PRINTER_DEVICE, SCALE_DEVICE

_ = lambda msg: gettext.dgettext("stoqdrivers", msg)

class BaseDevice(Logger):
    log_domain = "stoqdrivers"
    typename_translate_dict = {PRINTER_DEVICE: "Printer",
                               SCALE_DEVICE: "Scale"}
    # Subclasses must define these attributes
    device_dirname = None
    required_interfaces = None
    device_type = None
    
    def __init__(self, brand=None, model=None, device=None, config_file=None):
        Logger.__init__(self)
        if not self.device_dirname:
            raise ValueError("Subclasses must define the "
                             "`device_dirname' attribute")
        elif self.device_type is None:
            raise ValueError("device_type must be defined")
        self.brand, self.device, self.model = brand, device, model
        self._load_configuration(config_file)

    def _load_configuration(self, config_file):
        section_name = BaseDevice.typename_translate_dict[self.device_type]
        if not self.model or not self.brand or not self.device:
            self.config = StoqdriversConfig(config_file)
            if not self.config.has_section(section_name):
                raise ConfigError(_("There is no section named `%s'!")
                                  % section_name)
            self.brand = self.config.get_option("brand", section_name)
            self.device = self.config.get_option("device", section_name)
            self.model = self.config.get_option("model", section_name)

        name = "stoqdrivers.devices.%s.%s.%s" % (self.device_dirname,
                                                 self.brand, self.model)
        try:
            module = __import__(name, None, None, 'stoqdevices')
        except ImportError, reason:
            raise CriticalError("Could not load driver %s %s: %s"
                                % (self.brand.capitalize(),
                                   self.model.upper(), reason))
        class_name = self.model
        driver_class = getattr(module, class_name, None)
        if not driver_class:
            raise CriticalError("Device driver at %s needs a class called %s"
                                % (name, class_name))
        self._driver = driver_class(device=self.device)
        self.debug(("Config data: brand=%s,device=%s,model=%s\n"
                    % (self.brand, self.device, self.model)))
        self.check_interfaces()

    def get_model_name(self):
        return self._driver.model_name

    def check_interfaces(self):
        """ This method must be implemented in subclass and must ensure that the
        driver implements a valid interface for the current operation state.
        """
        raise NotImplementedError

    def notify_read(self, func):
        """ This function can be called when the callsite must know when data
        is coming from the serial port.   It is necessary that a gobject main
        loop is already running before calling this method.
        """
        gobject.io_add_watch(self._driver.fd, gobject.IO_IN,
                             lambda fd, cond: func(self, cond))
