#!/usr/bin/env python -u

import os
import threading
import functions
import re
import sys
from execcmd import ExecCmd
from config import Config

conf = Config('dpm.conf')
grubPath = conf.getValue('Paths', 'grub')
burgPath = conf.getValue('Paths', 'burg')
uvesafbPath = conf.getValue('Paths', 'uvesafb')
modulesPath = conf.getValue('Paths', 'modules')


# Save the selected Plymouth theme with its selected screen resolution
class SavePlymouthTheme(threading.Thread):
    def __init__(self, theme, resolution, rtobject):
        threading.Thread.__init__(self)
        self.theme = theme
        self.resolution = resolution
        self.rtobject = rtobject

    def run(self):
        self.delete = False
        boot = functions.getBoot()
        if boot == 'grub' or boot == 'burg':
            cmdSetTheme = 'plymouth-set-default-theme ' + self.theme
            cmdUpdGrub = 'update-grub'
            cmdUpdBurg = 'update-burg'
            cmdUpdInit = 'update-initramfs -u -k all'
            gbPath = grubPath
            if boot == 'burg':
                gbPath = burgPath
            
            if 'None:' in self.theme:
                self.delete = True
            
            # Filter out all custom parameters in GRUB_CMDLINE_LINUX_DEFAULT: we want to save them again
            # Read grub
            if boot == 'grub':
                gbFile = open(grubPath, 'r')
            else:
                gbFile = open(burgPath, 'r')
            gbText = gbFile.read()
            gbFile.close()
            # Get the GRUB_CMDLINE_LINUX_DEFAULT line
            regexpLinDef = 'GRUB_CMDLINE_LINUX_DEFAULT.*\n'
            linDef = re.search(regexpLinDef, gbText)
            #print linDef.group(0)
            # Delete all parameters we know
            delGroups = '(GRUB_CMDLINE_LINUX_DEFAULT=)|(quiet)|(splash)|(nomodeset)|(video=.*ywrap)|(\")'
            custParms = re.sub(delGroups, '', linDef.group(0))
            custParms = custParms.strip()

            if custParms != '':
                print cutParms
                # Cleanup the left overs
                custParms = re.sub(' +', ' ', custParms.strip())
                custParms = ' ' + custParms

            if self.delete:
                gbLinDef = "sed -i -e 's/\(GRUB_CMDLINE_LINUX_DEFAULT=\).*/\\1\"quiet" + custParms + "\"/' " + gbPath
                #gbGfxMode = "sed -i 's/^GRUB_GFXMODE.*/#GRUB_GFXMODE=640x480/g' " + gbPath
            else:
                gbLinDef = "sed -i -e 's/\(GRUB_CMDLINE_LINUX_DEFAULT=\).*/\\1\"quiet splash nomodeset video=uvesafb:mode_option=" + self.resolution + "-16,mtrr=3,scroll=ywrap" + custParms + "\"/' " + gbPath
                #gbGfxMode = "sed -i 's/^#GRUB_GFXMODE.*/GRUB_GFXMODE=800x600/g' " + gbPath
                #gbGfxMode = "sed -i -e 's/\(GRUB_GFXMODE=\).*/\\1" + self.resolution + "/' " + gbPath
                uvesafb = "echo \"options uvesafb mode_option=" + self.resolution + "-16 mtrr=3 scroll=ywrap\" > " + uvesafbPath
            
            print gbLinDef
            
            ec = ExecCmd()
            ec.realtime = True
            ec.rtobject = self.rtobject
            #ec.run('ping -c 10 www.google.com')
            
            # grub
            msg = 'Edit ' + gbPath + ': GRUB_CMDLINE_LINUX_DEFAULT'
            print msg
            ec.run(gbLinDef, msg)
            #msg = 'Edit ' + grubPath + ': GRUB_GFXMODE'
            #print msg
            #ec.run(gbGfxMode, msg)
            
            # modules
            if os.path.isfile(modulesPath):
                modFile = open(modulesPath, 'r')
                modText = modFile.read()
                modFile.close()
                
                # Search for values
                searchVal = 'uvesafb'
                matchObj = re.search(searchVal, modText)
                if not matchObj:
                    print 'Add ' + searchVal + ' to : ' + modulesPath
                    modText += '\n' + searchVal
                else:
                    if self.delete:
                        print "Delete " + searchVal + " from " + modulesPath
                        modText = modText.replace(searchVal, '')
                searchVal = 'vga16fb'
                matchObj = re.search(searchVal, modText)
                if not matchObj:
                    print 'Add ' + searchVal + ' to : ' + modulesPath
                    modText += '\n' + searchVal
                else:
                    if self.delete:
                        print "Delete " + searchVal + " from " + modulesPath
                        modText = modText.replace(searchVal, '')
                        
                modFile = open(modulesPath, 'w')
                modFile.write(modText)
                modFile.close()
                
            # uvesafb
            if self.delete:
                msg = 'Delete ' + uvesafbPath
                print msg
                ec.run('rm -f ' + uvesafbPath, msg)
            else:
                msg = 'Create ' + uvesafbPath
                print msg
                ec.run(uvesafb, msg)
            
            # Update
            if not self.delete:
                ec.run(cmdSetTheme)
            if boot == 'grub':
                ec.run(cmdUpdGrub)
            else:
                ec.run(cmdUpdBurg)
            ec.run(cmdUpdInit)
        else:
            print "This boot is not supported"