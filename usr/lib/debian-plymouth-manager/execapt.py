#!/usr/bin/env python -u

import threading
from execcmd import ExecCmd

class ExecuteApt(threading.Thread):
    def __init__(self, cb):
        threading.Thread.__init__(self)
        self.callback = cb
        
    def start(self, cmd, realtime=False, rtobject=object):
        self.aptok = True
        ec = ExecCmd()
        ec.realtime = realtime
        ec.rtobject = rtobject
        lst = ec.run(cmd)

        # Check if an error occured
        self.callback(True)
        for line in lst:
            if line[:2] == 'E:':
                self.callback(False)
                break
