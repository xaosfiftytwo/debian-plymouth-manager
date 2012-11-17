#!/usr/bin/env python

# Elevate permissions
import os
import functions
import getopt
import sys
import string
from config import Config
from logger import Logger

# Help
def usage():
    # Show usage
    hlp = """Usage: debian-plymouth-manager [options]

Options:
  -d (--debug): print debug information to log file in user directory
  -f (--force): force start in a live environment
  -h (--help): show this help"""
    print hlp


# Handle arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], 'hdf', ['help', 'debug', 'force'])
except getopt.GetoptError:
    usage()
    sys.exit(2)

debug = False
force = False
for opt, arg in opts:
    if opt in ('-d', '--debug'):
        debug = True
    if opt in ('-f', '--force'):
        force = True
    elif opt in ('-h', '--help'):
        usage()
        sys.exit()

# Initialize logging
logFile = ''
if debug:
    logFile = 'dpm.log'
log = Logger(logFile)
functions.log = log
if debug:
    if os.path.isfile(log.logPath):
        open(log.logPath, 'w').close()
    log.write('Write debug information to file: ' + log.logPath, 'main', 'info')

# Set variables
scriptDir = os.path.dirname(os.path.realpath(__file__))
conf = Config('dpm.conf')
livePath = conf.getValue('Paths', 'live')
ubiquityPath = conf.getValue('Paths', 'ubiquity')

# Pass arguments to dpm.py: replace - with : -> because kdesudo assumes these options are meant for him...
# Isn't there another way?
args = ' '.join(sys.argv[1:])
if len(args) > 0:
    args = ' ' + string.replace(args, '-', ':')
    # Pass the log path to dpm.py
    if debug:
        args += ' :l ' + log.logPath

if not functions.isRunningLive() or force:
    if functions.getDistribution().lower() != 'debian':
        # Not Debian
        log.write('Not running Debian: exiting', 'main', 'error')
    else:
        dpmPath = os.path.join(scriptDir, 'dpm.py' + args)

        # Add launcher string, only when not root
        launcher = ''
        if os.geteuid() > 0:
            if os.path.exists('/usr/bin/kdesudo'):
                launcher = 'kdesudo -i /usr/share/linuxmint/logo.png -d --comment "<b>Please enter your password</b>"'
            elif os.path.exists('/usr/bin/gksu'):
                launcher = 'gksu --message "<b>Please enter your password</b>"'

        cmd = '%s python %s' % (launcher, dpmPath)
        log.write('Startup command: ' + cmd, 'main', 'debug')
        os.system(cmd)
