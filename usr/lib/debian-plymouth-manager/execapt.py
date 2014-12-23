#! /usr/bin/env python3
#-*- coding: utf-8 -*-

import threading
import gettext
import utils

# i18n
gettext.install("debian-plymouth-manager", "/usr/share/locale")


class ExecuteApt(threading.Thread):
    def __init__(self, loggerObject, command, queue):
        threading.Thread.__init__(self)
        self.log = loggerObject
        self.queue = queue
        self.command = command

    def run(self):
        try:
            lst = utils.getoutput(self.command)
            print((str(lst)))
            # Check if an error occured
            for line in lst:
                if line[:2] == 'E:':
                    self.log.write(_("Error returned: %(err)s") % { "err": line }, 'execapt.run', 'error')
                    self.queue.put(line)
                    break
        except Exception as detail:
            self.queue.put(detail)
        finally:
            # If no error occurred, be sure to put None in the queue or get an error on task_done
            self.queue.put(None)
            self.queue.task_done()
