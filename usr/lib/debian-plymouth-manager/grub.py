#!/usr/bin/env python

import re
import os
import threading
import gettext
from config import Config
from execcmd import ExecCmd

# i18n
gettext.install("debian-plymouth-manager", "/usr/share/locale")


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

    # Get current Plymouth resolution
    def getCurrentResolution(self):
        res = None
        boot = self.getConfig()
        if boot:
            f = open(boot, 'r')
            grubLines = f.read().splitlines()
            f.close()
            for line in grubLines:
                # Search text for resolution
                matchObj = re.search('^GRUB_GFXMODE=(.*)', line)
                if matchObj:
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
        self.ec = ExecCmd(self.log)
        self.grub = Grub(self.log)
        self.resolution = resolution
        self.conf = Config('debian-plymouth-manager.conf')
        self.modulesPath = self.conf.getValue('Paths', 'modules')

    # Save given grub resolution
    def run(self):
        try:
            boot = self.grub.getConfig()

            if boot:
                cmd = 'sed -i -e \'/GRUB_GFXMODE=/ c GRUB_GFXMODE=%s\' %s' % (self.resolution, boot)
                self.ec.run(cmd)
                # Update grub and initram
                if 'grub' in boot:
                    self.ec.run('update-grub')
                else:
                    self.ec.run('update-burg')
            else:
                self.log.write(_("No grub or burg found"), 'GrubSave.run', 'error')

        except Exception, detail:
            self.log.write(detail, 'Grub.run', 'exception')
