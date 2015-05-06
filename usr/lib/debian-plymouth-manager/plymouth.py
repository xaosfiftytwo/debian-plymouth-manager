#! /usr/bin/env python3

# http://wiki.debian.org/plymouth
# https://wiki.ubuntu.com/Plymouth

import re
import os
import threading
import gettext
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
#_ = gettext.gettext


# Handles general plymouth functions
class Plymouth():
    def __init__(self, loggerObject):
        self.log = loggerObject
        self.grub = Grub(self.log)
        self.boot = self.grub.getConfig()
        self.avlThemesSearchstr = 'plymouth-themes'
        self.setThemePath = '/usr/sbin/plymouth-set-default-theme'
        self.modulesPath = '/etc/initramfs-tools/modules'

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
                    if ' splash' in matchObj.group(1):
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
        lines = []
        res = self.grub.getCurrentResolution()

        # The Wheezy way of configuring
        if res is None:
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
    def __init__(self, loggerObject, theme=None, resolution=None):
        threading.Thread.__init__(self)
        self.log = loggerObject
        self.grub = Grub(self.log)
        self.boot = self.grub.getConfig()
        self.theme = None
        self.resolution = None
        self.modulesPath = '/etc/initramfs-tools/modules'
        self.setThemePath = '/usr/sbin/plymouth-set-default-theme'
        self.plymouth = Plymouth(self.log)
        self.installedThemes = self.plymouth.getInstalledThemes()
        if theme in self.installedThemes and resolution is not None:
            self.log.write("Set theme: {0} ({1})".format(theme, resolution), 'PlymouthSave.init', 'debug')
            self.theme = theme
            self.resolution = resolution

    # Save given theme and resolution
    def run(self):
        try:
            if not os.path.exists(self.modulesPath):
                utils.shell_exec("touch {}".format(self.modulesPath))

            # Cleanup first
            utils.shell_exec("sed -i -e 's/^ *//; s/ *$//' %s" % self.modulesPath)    # Trim all lines
            utils.shell_exec("sed -i -e '/^.*KMS$/d' %s" % self.modulesPath)
            utils.shell_exec("sed -i -e '/^intel_agp$/d' %s" % self.modulesPath)
            utils.shell_exec("sed -i -e '/^drm$/d' %s" % self.modulesPath)
            utils.shell_exec("sed -i -e '/^nouveau modeset.*/d' %s" % self.modulesPath)
            utils.shell_exec("sed -i -e '/^radeon modeset.*/d' %s" % self.modulesPath)
            utils.shell_exec("sed -i -e '/^i915 modeset.*/d' %s" % self.modulesPath)
            utils.shell_exec("sed -i -e '/^uvesafb\s*mode_option.*/d' %s" % self.modulesPath)
            if os.path.exists(self.boot):
                utils.shell_exec("sed -i -e '/^GRUB_GFXPAYLOAD_LINUX.*/d' %s" % self.boot)
            splashFile = '/etc/initramfs-tools/conf.d/splash'
            if os.path.exists(splashFile):
                os.remove(splashFile)

            # Set/Unset splash
            cmd = "sed -i -e 's/\s*[a-z]*splash//' {}".format(self.boot)
            utils.shell_exec(cmd)
            if self.theme is None:
                self.log.write("Set nosplash", 'PlymouthSave.run', 'debug')
                cmd = "sed -i -e '/^GRUB_CMDLINE_LINUX_DEFAULT=/ s/\"$/ nosplash\"/' {}".format(self.boot)
                utils.shell_exec(cmd)
            else:
                self.log.write("Set splash", 'PlymouthSave.run', 'debug')
                cmd = "sed -i -e '/^GRUB_CMDLINE_LINUX_DEFAULT=/ s/\"$/ splash\"/' {}".format(self.boot)
                utils.shell_exec(cmd)
                # Set resolution
                if self.resolution is not None:
                    self.log.write("GRUB_GFXMODE={}".format(self.resolution), 'PlymouthSave.run', 'debug')
                    cmd = "sed -i -e '/GRUB_GFXMODE=/ c GRUB_GFXMODE={0}' {1}".format(self.resolution, self.boot)
                    utils.shell_exec(cmd)

            # Only for plymouth version older than 9
            if self.theme is not None and self.resolution is not None:
                plymouthVersion = utils.strToNumber(utils.getPackageVersion("plymouth").replace('.', '')[0:2], True)
                self.log.write("plymouthVersion={}".format(plymouthVersion), 'PlymouthSave.run', 'debug')
                if plymouthVersion < 9:
                    # Write uvesafb command to modules file
                    self.log.write("> Use uvesafb to configure Plymouth", 'PlymouthSave.run', 'debug')
                    line = "\nuvesafb mode_option=%s-24 mtrr=3 scroll=ywrap\ndrm\n" % self.resolution
                    with open(self.modulesPath, 'a') as f:
                        f.write(line)

                    # Use framebuffer
                    line = "FRAMEBUFFER=y"
                    with open('/etc/initramfs-tools/conf.d/splash', 'w') as f:
                        f.write(line)

            # Read grub for debugging purposes
            with open(self.boot, 'r') as f:
                content = f.read()
                self.log.write("\nNew grub:\n{}\n".format(content), 'PlymouthSave.run', 'debug')

            # Update grub
            if 'grub' in self.boot:
                utils.shell_exec('update-grub')
            else:
                utils.shell_exec('update-burg')

            # Set the theme and update initramfs
            if self.theme is not None:
                utils.shell_exec("{0} -R {1}".format(self.setThemePath, self.theme))

        except Exception as detail:
            self.log.write(detail, 'PlymouthSave.run', 'exception')
