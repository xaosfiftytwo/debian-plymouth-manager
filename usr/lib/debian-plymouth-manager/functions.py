#!/usr/bin/env python -u

import os
import sys
import subprocess
import re
from execcmd import ExecCmd
from config import Config
try:
    import gtk
except Exception, detail:
    print detail
    sys.exit(1)

conf = Config('dpm.conf')
grubPath = conf.getValue('Paths', 'grub')
burgPath = conf.getValue('Paths', 'burg')
avlThemesSearchstr = "plymouth-themes"

# General ================================================

# Return the type string of a object
def getTypeString(object):
    tpString = ""
    tp = str(type(object))
    matchObj = re.search("'(.*)'", tp)
    if matchObj:
        tpString = matchObj.group(1)
    return tpString


# Convert string to integer
def strToInt(str):
    try:
        i = int(str)
    except ValueError:
        i = 0
        
    return i

# TreeView ==============================================

# Clear treeview
def clearTreeView(treeview):
    liststore = treeview.get_model()
    if liststore != None:
        liststore.clear()
        treeview.set_model(liststore)

# Append row to single columned treeview
def appendRowToTreeView(listview, value, appendToTop=False):
    liststore = vieview.get_model()
    setCursor = 0
    w = 400
    if liststore == None:
        column0 = gtk.TreeViewColumn("Column 0", gtk.CellRendererText(), text=0, weight=1)
        column0.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        treeview.append_column(column0)  
        liststore = gtk.ListStore(str, int)
    if appendToTop:
        iter = liststore.insert(0, [value, w])
    else:
        iter = liststore.append([value, w])
        setCursor = len(list) - 1
    view.set_model(liststore)
    view.set_cursor(setCursor)
    # Scroll to selected cursor
    path = liststore.get_path(iter)
    listview.scroll_to_cell(path)

# General function to fill a single columned treeview
# Set setCursorWeight to 400 if you don't want bold font
def fillTreeview(treeview, contentList, setCursor=0, setCursorWeight=400):
    if len(contentList) > 0:
        liststore = gtk.ListStore(str, int)
        for i in range(len(contentList)):
            w = 400
            if i == setCursor:
                w = setCursorWeight
            liststore.append([contentList[i], w])

        # define columns
        #column0 = gtk.TreeViewColumn("Column 0", gtk.CellRendererText(), text=0, foreground=1, background=2, weight=3)
        column0 = gtk.TreeViewColumn("Column 0", gtk.CellRendererText(), text=0, weight=1)
        column0.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        treeview.append_column(column0)            
        treeview.set_model(liststore)
        treeview.set_cursor(setCursor)
        # Scroll to selected cursor
        selection = treeview.get_selection()
        tm, treeIter = selection.get_selected()
        path = tm.get_path(treeIter)
        treeview.scroll_to_cell(path)

# Get the selected value in a treeview
def getSelectedValue(listview):
    # Assume single row selection
    (model,pathlist) = listview.get_selection().get_selected_rows()
    return model.get_value(model.get_iter(pathlist[0]), 0)

# Statusbar =====================================================

def pushMessage(statusbar, message, contextString='message'):
    context = statusbar.get_context_id(contextString)
    statusbar.push(context, message)

def popMessage(statusbar, contextString='message'):
    context = statusbar.get_context_id(contextString)
    statusbar.pop(context)

# System ========================================================

# Get valid screen resolutions
def getResolutions(minRes, maxRes):
    cmd = 'xrandr'
    ec = ExecCmd()
    cmdList = ec.run(cmd)
    avlRes = [] # Available Resolutions

    # Split the minimum and maximum resolutions
    minResList = minRes.split('x')
    maxResList = maxRes.split('x')
    minW = strToInt(minResList[0])
    minH = strToInt(minResList[1])
    maxW = strToInt(maxResList[0])
    maxH = strToInt(maxResList[1])

    # Fill the list with screen resolutions
    for line in cmdList:
        for item in line.split():
            if item and 'x' in item and len(item) > 2 and not '+' in item and not 'axis' in item and not 'maximum' in item:
                itemList = item.split('x')
                itemW = strToInt(itemList[0])
                itemH = strToInt(itemList[1])
                # Check if it can be added
                if itemW >= minW and itemW <= maxW and itemH >= minH and itemH <= maxH:
                    avlRes.append(item)
    return avlRes

# Get current Plymouth resolution
def getCurrentResolution():
    res = ""
    regExp = "mode_option=(.*)-"
    # Open grub
    if os.path.isfile(grubPath):
        grubFile = open(grubPath,'r')
        grubText = grubFile.read()
        grubFile.close()
        # Search text for resolution
        matchObj = re.search(regExp, grubText)
        if matchObj:
            res = matchObj.group(1)
        
    return res

# Get the bootloader
def getBoot():
    if os.path.isfile(grubPath): # Grub
        return 'grub'
    elif os.path.isfile(burgPath): # Burg
        return 'burg'
    else:
        return ''

# Plymouth =============================================

# Get a list of installed Plymouth themes
def getInstalledThemes():
    cmd = '/usr/sbin/plymouth-set-default-theme --list'
    ec = ExecCmd()
    instThemes = ec.run(cmd)
    return instThemes

# Get the currently used Plymouth theme
def getCurrentTheme():
    curTheme = ['']
    if getCurrentResolution() != '':
        cmd = '/usr/sbin/plymouth-set-default-theme'
        ec = ExecCmd()
        curTheme = ec.run(cmd)
    return curTheme[0]

# Get a list of Plymouth themes in the repositories that can be installed
def getAvailableThemes():
    startmatch = '39m-'
    cmd = 'apt search ' + avlThemesSearchstr + ' | grep ^p'
    ec = ExecCmd()
    cmdList = ec.run(cmd)
    avlThemes = []

    for line in cmdList:
        if not startmatch + 'all' in line:
            matchObj = re.search(startmatch + '([a-z]|-)*', line)
            if matchObj:
                avlThemes.append(matchObj.group().replace(startmatch, ''))

    return avlThemes

def previewPlymouth():
    prevPath = '/usr/bin/debian-plymouth-preview'
    if not os.path.isfile(prevPath):
        prevFile = open(prevPath, 'w')
        prevFile.write('#!/bin/bash\nplymouthd; plymouth --show-splash ; for ((I=0; I<10; I++)); do plymouth --update=test$I ; sleep 1; done; plymouth quit')
        prevFile.close()
    os.chmod(prevPath, 755)
    cmd = 'su -c ' + prevPath
    ec = ExecCmd()
    ec.run(cmd)

# Apt ==============================================

# Get the package name that can be uninstalled of a given Plymouth theme
def getRemovablePackageName(theme):
    cmd = 'dpkg -S ' + theme + '.plymouth'
    print cmd
    package = ''
    ec = ExecCmd()
    packageNames = ec.run(cmd)

    for line in packageNames:
        if avlThemesSearchstr in line:
            matchObj = re.search('(^.*):', line)
            if matchObj:
                package = matchObj.group(1)
                break
    print package
    return package

# Get valid package name of a Plymouth theme (does not have to exist in the repositories)
def getPackageName(theme):
    return avlThemesSearchstr + "-" + theme


