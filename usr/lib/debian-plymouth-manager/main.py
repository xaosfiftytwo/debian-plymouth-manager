#!/usr/bin/python

# Elevate permissions
import os
import functions
from execcmd import ExecCmd
from dialogs import MessageDialog
from config import Config
try:
    import gtk
except Exception, detail:
    print detail
    sys.exit(1)

conf = Config('dpm.conf')
livePath = conf.getValue('Paths', 'live')
debCmd = 'cat /etc/*-release | grep ebian | wc -l'


if os.path.isfile(livePath):
    msg = "You cannot run this program in a live environment."
    MessageDialog("Live environment check", msg , gtk.MESSAGE_INFO).show()
else:
    ec = ExecCmd()
    deb = ec.run(debCmd)
    if deb[0] == 0:
        # Not Debian
        msg = "You are not running Debian and cannot run this program.\nDoing so will harm your system."
        MessageDialog("Distribution check", msg , gtk.MESSAGE_INFO).show()
    else:
        dpmPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "dpm.py")

        if os.path.exists("/usr/bin/kdesudo"):
            launcher = "kdesudo -i /usr/share/linuxmint/logo.png -d --comment \"<b>Please enter your password</b>\""
        elif os.path.exists("/usr/bin/gksu"):
            launcher = "gksu --message \"<b>Please enter your password</b>\""

        cmd = "%s python %s" % (launcher, dpmPath)
        #print cmd
        os.system(cmd)