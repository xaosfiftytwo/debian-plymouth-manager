#!/usr/bin/env python

# Elevate permissions
import os
import functions
import getopt
import sys
import string
from logger import Logger


# Help
def usage():
    # Show usage
    hlp = """Usage: spm [options]

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
    log.write('Write debug information to file: %s' % log.logPath, 'main', 'info')

# Log some basic environmental information
machineInfo = functions.getSystemVersionInfo()
log.write('Machine info: %s' % machineInfo, 'main', 'info')
version = functions.getPackageVersion('ddm')
log.write('DDM version: %s' % version, 'main', 'info')

# There were issues with apt-listbugs
# Warn the user for any errors that might accur when apt-listbugs is installed
if functions.isPackageInstalled('apt-listbugs'):
    log.write('apt-listbugs is installed and might interfere with driver installation', 'main', 'warning')

# Set variables
scriptDir = os.path.dirname(os.path.realpath(__file__))

# Pass arguments to ddm.py: replace - with : -> because kdesudo assumes these options are meant for him...
# TODO: Isn't there another way?
args = ' '.join(sys.argv[1:])
if len(args) > 0:
    args = ' ' + string.replace(args, '-', ':')
    # Pass the log path to ddm.py
    if debug:
        args += ' :l ' + log.logPath

if functions.getDistribution() == 'debian':
    # Do not run in live environment
    if not functions.isRunningLive() or force:
        dpmPath = os.path.join(scriptDir, 'dpm.py' + args)

        # Add launcher string, only when not root
        launcher = ''
        if os.geteuid() > 0:
            if os.path.exists('/usr/bin/kdesudo'):
                launcher = 'kdesudo -i /usr/share/dpm/logo.png -d --comment "<b>Please enter your password</b>"'
            elif os.path.exists('/usr/bin/gksu'):
                launcher = 'gksu --message "<b>Please enter your password</b>"'

        cmd = '%s python %s' % (launcher, dpmPath)
        log.write('Startup command: ' + cmd, 'main', 'debug')
        os.system(cmd)
    else:
        log.write('Use --force to run DPM in a live environment', 'main', 'warning')
else:
    log.write('DPM can only run in Debian based distributions', 'main', 'warning')
