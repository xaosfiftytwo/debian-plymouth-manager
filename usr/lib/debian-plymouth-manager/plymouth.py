#! /usr/bin/env python3
#-*- coding: utf-8 -*-

# http://wiki.debian.org/plymouth
# https://wiki.ubuntu.com/Plymouth

import re
import os
import threading
import gettext
from glob import glob
import utils
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
    def __init__(self, loggerObject, setThemePath, modulesPath):
        self.log = loggerObject
        self.grub = Grub(self.log)
        self.boot = self.grub.getConfig()
        self.avlThemesSearchstr = 'plymouth-themes'
        self.setThemePath = setThemePath
        self.modulesPath = modulesPath

    # Get a list of installed Plymouth themes
    def getInstalledThemes(self):
        instThemes = []
        if os.path.isfile(self.setThemePath):
            cmd = '%s --list' % self.setThemePath
            instThemes = utils.getoutput(cmd)
        return instThemes

    # Get the currently used Plymouth theme
    def getCurrentTheme(self):
        curTheme = None
        if os.path.isfile(self.setThemePath):
            if self.boot is not None:
                grubCont = ""
                with open(self.boot, 'r') as f:
                    grubCont = f.read()
                matchObj = re.search('GRUB_CMDLINE_LINUX_DEFAULT="(.*)"', grubCont)
                if matchObj:
                    if 'splash' in matchObj.group(1):
                        curThemeList = utils.getoutput(self.setThemePath)
                        if curThemeList:
                            curTheme = curThemeList[0]
        return curTheme

    # Get a list of Plymouth themes in the repositories that can be installed
    def getAvailableThemes(self):
        cmd = 'aptitude search %s | grep ^p' % self.avlThemesSearchstr
        availableThemes = utils.getoutput(cmd)
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
            utils.shell_exec(cmd)
        except Exception as detail:
            self.log.write(detail, 'plymouth.previewPlymouth', 'error')

    # Get the package name that can be uninstalled of a given Plymouth theme
    def getRemovablePackageName(self, theme):
        cmd = 'dpkg -S %s.plymouth' % theme
        package = None
        packageNames = utils.getoutput(cmd)

        for line in packageNames:
            if self.avlThemesSearchstr in line:
                matchObj = re.search('(^.*):', line)
                if matchObj:
                    package = matchObj.group(1)
                    break
        self.log.write("Package found %(pck)s" % { "pck": package }, 'plymouth.getRemovablePackageName', 'debug')
        return package

    # Get valid package name of a Plymouth theme (does not have to exist in the repositories)
    def getPackageName(self, theme):
        return self.avlThemesSearchstr + "-" + theme

    # Get current Plymouth resolution
    def getCurrentResolution(self):
        res = None
        lines = []
        with open(self.modulesPath, 'r') as f:
            lines = f.readlines()
        for line in lines:
            matchObj = re.search('^uvesafb\s+mode_option\s*=\s*([0-9x]+)', line)
            if matchObj:
                res = matchObj.group(1)
                self.log.write("Current Plymouth resolution: %(res)s" % { "res": res }, 'plymouth.getCurrentResolution', 'debug')
                break

        # Old way of configuring Plymouth
        if res is None:
            if self.boot is not None:
                with open(self.boot, 'r') as f:
                    lines = f.readlines()
                for line in lines:
                    # Search text for resolution
                    matchObj = re.search('^GRUB_GFXPAYLOAD_LINUX=(.*)', line)
                    if matchObj:
                        res = matchObj.group(1)
                        self.log.write("Current Plymouth resolution: %(res)s" % { "res": res }, 'plymouth.getCurrentResolution', 'debug')
                        break
            else:
                self.log.write(_("Neither grub nor burg found in /etc/default"), 'plymouth.getCurrentResolution', 'error')
        return res


# Handles plymouth saving (threaded)
class PlymouthSave(threading.Thread):
    def __init__(self, loggerObject, modulesPath, splashPath, setThemePath, theme=None, resolution=None):
        threading.Thread.__init__(self)
        self.log = loggerObject
        self.grub = Grub(self.log)
        self.boot = self.grub.getConfig()
        self.theme = None
        self.resolution = None
        self.modulesPath = modulesPath
        self.splashPath = splashPath
        self.setThemePath = setThemePath
        self.plymouth = Plymouth(self.log, setThemePath, modulesPath)
        self.installedThemes = self.plymouth.getInstalledThemes()
        if theme in self.installedThemes and resolution is not None:
            print((">> Theme installed and selected: {}".format(theme)))
            self.theme = theme
            self.resolution = resolution

    # Save given theme and resolution
    def run(self):
        try:
            if not os.path.exists(self.modulesPath):
                self.log.write(_("Cannot save Plymouth theme:\nNo %s.") % self.modulesPath, 'PlymouthSave.run', 'error')
            else:
                # Cleanup first
                utils.shell_exec("sed -i -e 's/^ *//; s/ *$//' %s" % self.modulesPath)    # Trim all lines
                utils.shell_exec("sed -i -e 's/^.*KMS$//g' %s" % self.modulesPath)
                utils.shell_exec("sed -i -e 's/^intel_agp$//g' %s" % self.modulesPath)
                utils.shell_exec("sed -i -e 's/^drm$//g' %s" % self.modulesPath)
                utils.shell_exec("sed -i -e 's/^nouveau modeset.*//g' %s" % self.modulesPath)
                utils.shell_exec("sed -i -e 's/^radeon modeset.*//g' %s" % self.modulesPath)
                utils.shell_exec("sed -i -e 's/^i915 modeset.*//g' %s" % self.modulesPath)
                utils.shell_exec("sed -i -e 's/^uvesafb\s*mode_option.*//g' %s" % self.modulesPath)
                utils.shell_exec("sed -i -e '/^$/d' %s" % self.modulesPath)    # Remove empty lines
                if os.path.exists(self.boot):
                    utils.shell_exec("sed -i -e 's/^GRUB_GFXPAYLOAD_LINUX.*//g' %s" % self.boot)
                utils.shell_exec("rm %s" % self.splashPath)

                # Edit grub
                if self.theme is not None \
                    and not utils.hasStringInFile("splash", self.boot):
                    cmd = "sed -i -e 's/quiet/quiet splash/' {}".format(self.boot)
                    print((">> cmd={}".format(cmd)))
                    utils.shell_exec(cmd)

                # Write uvesafb command to modules file
                if self.theme is not None and self.resolution is not None:
                    line = "\nuvesafb mode_option=%s-24 mtrr=3 scroll=ywrap\ndrm\n" % self.resolution
                    with open(self.modulesPath, 'a') as f:
                        f.write(line)

                    # Use framebuffer
                    line = "FRAMEBUFFER=y"
                    with open(self.splashPath, 'w') as f:
                        f.write(line)

                # Read grub for debugging purposes
                with open(self.boot, 'r') as f:
                    content = f.read()
                    self.log.write("\nNew grub:\n%(grub)s\n" % { "grub": content }, 'PlymouthSave.run', 'debug')

                # Set the theme
                if self.theme is not None:
                    utils.shell_exec('%s %s' % (self.setThemePath, self.theme))

                # Update grub and initram
                if 'grub' in self.boot:
                    utils.shell_exec('update-grub')
                else:
                    utils.shell_exec('update-burg')
                if self.theme is not None:
                    utils.shell_exec('update-initramfs -u -k all')

        except Exception as detail:
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
