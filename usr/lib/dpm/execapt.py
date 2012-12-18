#!/usr/bin/env python -u

import threading
from execcmd import ExecCmd


class ExecuteApt(threading.Thread):
    def __init__(self, loggerObject, command, queue):
        threading.Thread.__init__(self)
        self.log = loggerObject
        self.queue = queue
        self.command = command

    def run(self):
        try:
            ec = ExecCmd(self.log)
            lst = ec.run(self.command)
            print str(lst)
            # Check if an error occured
            for line in lst:
                if line[:2] == 'E:':
                    self.log.write('Error returned: %s' % line, 'execapt.run', 'error')
                    self.queue.put(line)
                    break
        except Exception, detail:
            self.queue.put(detail)
        finally:
            # If no error occurred, be sure to put None in the queue or get an error on task_done
            self.queue.put(None)
            self.queue.task_done()
