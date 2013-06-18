#!/usr/bin/env python

# http://wiki.debian.org/plymouth
# https://wiki.ubuntu.com/Plymouth

import re
import os
import threading
import functions
import gettext
from glob import glob
from execcmd import ExecCmd
from config import Config
from grub import Grub

kmsDrv = ['nouveau', 'radeon', 'intel']

manufacturerDrivers = [
['ATI', ['fglrx', 'radeonhd', 'radeon', 'fbdev', 'vesa']],
['NVIDIA', ['nvidia', 'nouveau', 'fbdev', 'vesa']],
['VIA', ['chrome9', 'openchrome', 'unichrome']],
['INTEL', ['intel', 'fbdev', 'vesa']],
['VBOXVIDEO', ['vboxvideo']]
]

# i18n
gettext.install("debian-plymouth-manager", "/usr/share/locale")


# Handles general plymouth functions
class Plymouth():
    def __init__(self, loggerObject):
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.grub = Grub(self.log)
        self.avlThemesSearchstr = 'plymouth-themes'
        self.conf = Config('debian-plymouth-manager.conf')
        self.setThemePath = self.conf.getValue('Paths', 'settheme')

    # Get a list of installed Plymouth themes
    def getInstalledThemes(self):
        instThemes = []
        if os.path.isfile(self.setThemePath):
            cmd = '%s --list' % self.setThemePath
            instThemes = self.ec.run(cmd, False)
        return instThemes

    # Get the currently used Plymouth theme
    def getCurrentTheme(self):
        curTheme = None
        if os.path.isfile(self.setThemePath):
            boot = self.grub.getConfig()
            if boot is not None:
                f = open(boot, 'r')
                grubCont = f.read()
                f.close()
                matchObj = re.search('GRUB_CMDLINE_LINUX_DEFAULT="(.*)"', grubCont)
                if matchObj:
                    if 'splash' in matchObj.group(1):
                        curThemeList = self.ec.run(self.setThemePath, False)
                        if curThemeList:
                            curTheme = curThemeList[0]
        return curTheme

    # Get a list of Plymouth themes in the repositories that can be installed
    def getAvailableThemes(self):
        cmd = 'aptitude search %s | grep ^p' % self.avlThemesSearchstr
        availableThemes = self.ec.run(cmd)
        avlThemes = []

        for line in availableThemes:
            matchObj = re.search('%s-([a-zA-Z0-9-]*)' % self.avlThemesSearchstr, line)
            if matchObj:
                theme = matchObj.group(1)
                if not 'all' in theme:
                    avlThemes.append(theme)

        return avlThemes

    def previewPlymouth(self):
        try:
            cmd = "su -c 'plymouthd; plymouth --show-splash ; for ((I=0; I<10; I++)); do plymouth --update=test$I ; sleep 1; done; plymouth quit'"
            self.ec.run(cmd, False)
        except Exception, detail:
            self.log.write(detail, 'plymouth.previewPlymouth', 'error')

    # Get the package name that can be uninstalled of a given Plymouth theme
    def getRemovablePackageName(self, theme):
        cmd = 'dpkg -S %s.plymouth' % theme
        package = None
        packageNames = self.ec.run(cmd, False)

        for line in packageNames:
            if self.avlThemesSearchstr in line:
                matchObj = re.search('(^.*):', line)
                if matchObj:
                    package = matchObj.group(1)
                    break
        self.log.write(_("Package found %(pck)s") % { "pck": package }, 'plymouth.getRemovablePackageName', 'debug')
        return package

    # Get valid package name of a Plymouth theme (does not have to exist in the repositories)
    def getPackageName(self, theme):
        return self.avlThemesSearchstr + "-" + theme

    # Get current Plymouth resolution
    def getCurrentResolution(self):
        res = None
        boot = self.grub.getConfig()
        if boot:
            f = open(boot, 'r')
            grubLines = f.read().splitlines()
            f.close()
            for line in grubLines:
                # Search text for resolution
                matchObj = re.search('^GRUB_GFXPAYLOAD_LINUX=(.*)', line)
                if matchObj:
                    res = matchObj.group(1)
                    self.log.write(_("Current Plymouth resolution: %(res)s") % { "res": res }, 'plymouth.getCurrentResolution', 'debug')
                    break
        else:
            self.log.write(_("Neither grub nor burg found in /etc/default"), 'plymouth.getCurrentResolution', 'error')
        return res


# Handles plymouth saving (threaded)
class PlymouthSave(threading.Thread):
    def __init__(self, loggerObject, theme=None, resolution=None):
        threading.Thread.__init__(self)
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.grub = Grub(self.log)
        self.theme = None
        self.resolution = None
        self.plymouth = Plymouth(self.log)
        self.conf = Config('debian-plymouth-manager.conf')
        self.modulesPath = self.conf.getValue('Paths', 'modules')
        self.setThemePath = self.conf.getValue('Paths', 'settheme')
        self.installedThemes = self.plymouth.getInstalledThemes()
        if theme in self.installedThemes:
            self.theme = theme
            self.resolution = resolution

    # Save given theme and resolution
    def run(self):
        try:
            boot = self.grub.getConfig()
            module = self.getUsedDriver()
            # Test
            #module = 'vesa'

            if boot and module:
                # Create list with module lines per manufacturer
                kmsLines = []
                kmsLines.append([kmsDrv[2], 'intel_agp'])
                kmsLines.append(['all', 'drm'])
                # nouveau causes a tremendous amount of trouble when you switch to nvidia later on (blacklisting not enough)
                #kmsLines.append([kmsDrv[0], 'nouveau modeset=1'])
                kmsLines.append([kmsDrv[1], 'radeon modeset=1'])
                kmsLines.append([kmsDrv[2], 'i915 modeset=1'])

                # Cleanup first
                self.ec.run("sed 's/^ *//; s/ *$//' %s -i" % self.modulesPath, False)    # Trim all lines
                self.ec.run("sed 's/^.*KMS$//g' %s -i" % self.modulesPath, False)
                self.ec.run("sed 's/^intel_agp$//g' %s -i" % self.modulesPath, False)
                self.ec.run("sed 's/^drm$//g' %s -i" % self.modulesPath, False)
                self.ec.run("sed 's/^nouveau modeset.*//g' %s -i" % self.modulesPath, False)
                self.ec.run("sed 's/^radeon modeset.*//g' %s -i" % self.modulesPath, False)
                self.ec.run("sed 's/^i915 modeset.*//g' %s -i" % self.modulesPath, False)
                self.ec.run("sed '/^$/d' %s -i" % self.modulesPath, False)    # Remove empty lines

                if self.theme and self.resolution:
                    f = open(self.modulesPath, 'a')
                    f.write('\n# KMS\n')
                    for line in kmsLines:
                        if kmsDrv[0] in module and (line[0] == kmsDrv[0] or line[0] == 'all'):
                            f.write('%s\n' % line[1])
                        elif kmsDrv[1] in module and (line[0] == kmsDrv[1] or line[0] == 'all'):
                            f.write('%s\n' % line[1])
                        elif kmsDrv[2] in module and (line[0] == kmsDrv[2] or line[0] == 'all'):
                            f.write('%s\n' % line[1])
                        elif line[0] == 'all':
                            f.write('%s\n' % line[1])
                    f.close()

                # Read modules just for debugging purposes
                f = open(self.modulesPath, 'r')
                newModules = f.read()
                f.close()
                self.log.write(_("\nNew modules:\n%(modules)s\n") % { "modules": newModules }, 'PlymouthSave.run', 'debug')

                # Edit grub
                cmd = 'sed -i -e \'/GRUB_CMDLINE_LINUX_DEFAULT=/ c GRUB_CMDLINE_LINUX_DEFAULT="quiet"\' %s' % boot
                if self.theme:
                    cmd = 'sed -i -e \'/GRUB_CMDLINE_LINUX_DEFAULT=/ c GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"\' %s' % boot
                self.ec.run(cmd)

                cmd = "sed 's/^GRUB_GFXPAYLOAD_LINUX.*//g' %s -i" % boot
                if self.theme and self.resolution:
                    if functions.doesFileContainString(boot, 'GRUB_GFXPAYLOAD_LINUX'):
                        cmd = 'sed -i -e \'/GRUB_GFXPAYLOAD_LINUX=/ c GRUB_GFXPAYLOAD_LINUX=%s\' %s' % (self.resolution, boot)
                    else:
                        cmd = 'sed -i -e \'/GRUB_GFXMODE=/ i \GRUB_GFXPAYLOAD_LINUX=%s\' %s' % (self.resolution, boot)
                self.ec.run(cmd)

                # Read grub for debugging purposes
                f = open(boot, 'r')
                newGrub = f.read()
                f.close()
                self.log.write(_("\nNew grub:\n%(grub)s\n") % { "grub": newGrub }, 'PlymouthSave.run', 'debug')

                # Set the theme
                if self.theme:
                    self.ec.run('%s %s' % (self.setThemePath, self.theme))

                # Update grub and initram
                if 'grub' in boot:
                    self.ec.run('update-grub')
                else:
                    self.ec.run('update-burg')
                self.ec.run('update-initramfs -u -k all')
            else:
                self.log.write(_("Cannot save Plymouth theme:\nNo grub or burg config file in /etc/default."), 'PlymouthSave.run', 'error')

        except Exception, detail:
            self.log.write(detail, 'PlymouthSave.run', 'exception')

    # Return graphics module used by X.org
    def getUsedDriver(self):
        # find the most recent X.org log
        module = None
        logDir = '/var/log/'
        logPath = None
        maxTime = 0
        for f in glob(os.path.join(os.path.join(logDir, 'Xorg.*.log'))):
            mtime = os.stat(f).st_mtime
            if mtime > maxTime:
                maxTime = mtime
                logPath = f

        # Open the log file
        lines = []
        with open(logPath) as f:
            lines = list(f.read().splitlines())

        # Search for "randr" in each line and check the previous line for the used module
        lineCnt = -1
        for line in lines:
            lineCnt += 1
            matchObj = re.search('\)\srandr\s', line, flags=re.IGNORECASE)
            if matchObj:
                prevLine = lines[lineCnt - 1].lower()
                module = self.matchModuleInString(prevLine)
                break

        self.log.write(_("Used graphics driver: %(drv)s") % { "drv": module }, 'PlymouthSave.getUsedModule', 'info')
        return module

    # Return the module found in a string (used by getUsedModule)
    def matchModuleInString(self, text):
        for manDrv in manufacturerDrivers:
            for mod in manDrv[1]:
                if mod in text:
                    return mod
        return None
