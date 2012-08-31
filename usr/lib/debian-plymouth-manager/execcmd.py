#!/usr/bin/env python

import sys
import subprocess
import re
import functions
try:
    import gtk
except Exception, detail:
    print detail
    sys.exit(1)


# Class to execute a command and return the output in an array
class ExecCmd(object):
    def __init__(self):
        self.realtime = False
        def get_realtime(self):
            return self.__realtime
        def set_realtime(self, val):
            self.__realtime = val
        realtime = property(fget=get_realtime, fset=set_realtime)

        self.rtobject = object
        def get_rtobject(self):
            return self.__rtobject
        def set_rtobject(self, object):
            self.__rtobject = object
        rtobject = property(fget=get_rtobject, fset=set_rtobject)
        
    def run(self, cmd, defaultMessage=''):
        print cmd
        if self.realtime:
            tpStr = functions.getTypeString(self.rtobject)
            self.realTimeWrite(defaultMessage, True)
        
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        lstOut = []
        while True:
            line = p.stdout.readline().strip()
            if line == '' and p.poll() != None:
                break
            
            if line != '':
                lstOut.append(line)
                print ">>> " + line
                sys.stdout.flush()
                self.realTimeWrite(line)
            
        return lstOut
    
    # Real-time update of line
    def realTimeWrite(self, line, init=False):
        if self.realtime:
            tpStr = functions.getTypeString(self.rtobject)
            if tpStr != '':
                if tpStr == 'gtk.Label':
                    if init:
                        print 'Type = Label'
                    self.rtobject.set_text(line)
                elif tpStr == 'gtk.TreeView':
                    if init:
                        print 'Type = TreeView'
                        functions.clearTreeView(self.rtobject)
                    else:
                        functions.appendRowToTreeView(self.rtobject, line, True)
                elif tpStr == 'gtk.Statusbar':
                    if init:
                        print 'Type = gtk.Statusbar'
                    functions.pushMessage(self.rtobject, line)
                else:
                    print tpStr + ' not implemented'
                    tpStr = ''
                
                # Force repaint: ugly, but gui gets repainted so fast that gtk objects don't show it
                while gtk.events_pending():
                    gtk.main_iteration(False)