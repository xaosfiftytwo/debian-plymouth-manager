#! /usr/bin/env python3

import re
import os
import threading
import utils

# i18n: http://docs.python.org/3/library/gettext.html
import gettext
from gettext import gettext as _
gettext.textdomain('debian-plymouth-manager')


# Handles general plymouth functions
class Grub():
    def __init__(self, loggerObject):
        self.log = loggerObject

    # Get the bootloader
    def getConfig(self):
        grubPath = '/etc/default/grub'
        burgPath = '/etc/default/burg'
        if os.path.isfile(grubPath):  # Grub
            return grubPath
        elif os.path.isfile(burgPath):  # Burg
            return burgPath
        else:
            return None

    # Get current Grub resolution
    def getCurrentResolution(self):
        res = None
        boot = self.getConfig()
        if boot is not None:
            lines = []
            with open(boot, 'r') as f:
                lines = f.read().splitlines()
            for line in lines:
                # Search text for resolution
                matchObj = re.search('^GRUB_GFXMODE=(.*)', line)
                if matchObj:
                    if matchObj.group(1).strip() != "":
                        res = matchObj.group(1)
                        self.log.write("Current grub resolution: %(res)s" % { "res": res }, 'grub.getCurrentResolution', 'debug')
                    break
        else:
            self.log.write(_("Neither grub nor burg found in /etc/default"), 'grub.getCurrentResolution', 'error')
        return res


class GrubSave(threading.Thread):
    def __init__(self, loggerObject, resolution):
        threading.Thread.__init__(self)
        self.log = loggerObject
        self.grub = Grub(self.log)
        self.resolution = resolution

    # Save given grub resolution
    def run(self):
        try:
            boot = self.grub.getConfig()

            if boot and self.resolution is not None:
                cmd = 'sed -i -e \'/GRUB_GFXMODE=/ c GRUB_GFXMODE=%s\' %s' % (self.resolution, boot)
                utils.shell_exec(cmd)
                # Update grub and initram
                if 'grub' in boot:
                    utils.shell_exec('update-grub')
                else:
                    utils.shell_exec('update-burg')
            else:
                self.log.write(_("No grub or burg found"), 'GrubSave.run', 'error')

        except Exception as detail:
            self.log.write(detail, 'Grub.run', 'exception')
