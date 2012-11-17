#!/usr/bin/env python -u

import threading
from execcmd import ExecCmd


class ExecuteApt(threading.Thread):
    def __init__(self, cb, loggerObject, command):
        threading.Thread.__init__(self)
        self.log = loggerObject
        self.callback = cb
        self.command = command

    def run(self):
        try:
            if self.command != '':
                ec = ExecCmd(self.log)
                lst = ec.run(self.command)

                # Check if an error occured
                self.callback(True)
                for line in lst:
                    if line[:2] == 'E:':
                        self.log.write('Error returned: ' + line, 'execapt.run', 'error')
                        self.callback(False)
                        break
            else:
                self.log.write('Command not set, use setCommand(command)', 'execapt.run', 'error')

        except Exception, detail:
            self.log.write(detail, 'execapt.run', 'exception')
