#! /usr/bin/env python3

from gi.repository import Gtk, GObject, GLib
import utils
import threading
from queue import Queue
from os.path import join, dirname, realpath
from plymouth import Plymouth, PlymouthSave
from treeview import TreeViewHandler
from dialogs import MessageDialogSafe, QuestionDialog
from logger import Logger
from execapt import ExecuteApt
from grub import Grub, GrubSave


menuItems = ['themes', 'install', 'grub']

# i18n: http://docs.python.org/3/library/gettext.html
import gettext
from gettext import gettext as _
gettext.textdomain('debian-plymouth-manager')

# Need to initiate threads for Gtk
GObject.threads_init()


#class for the main window
class DPM:

    def __init__(self):
        self.scriptDir = dirname(realpath(__file__))
        # Load window and widgets
        self.builder = Gtk.Builder()
        self.builder.add_from_file(join(self.scriptDir, '../../share/debian-plymouth-manager/debian-plymouth-manager.glade'))

        # Main window objects
        go = self.builder.get_object
        self.window = go('dpmWindow')
        self.tv1 = go('tv1')
        self.tv2 = go('tv2')
        self.sw2 = go('sw2')
        self.statusbar = go('statusbar')
        self.btnPlymouth = go('btnPlymouth')
        self.btnThemes = go('btnThemes')
        self.btnGrub = go('btnGrub')
        self.pbDPM = go('pbDPM')
        self.btn1 = go('btn1')
        self.btn2 = go('btn2')
        self.lblTitle1 = go('lblTitle1')
        self.lblTitle2 = go('lblTitle2')

        # Translations
        title = _("Debian Plymouth Manager")
        self.window.set_title(title)
        self.btnPlymouth.set_label("_" + _("Plymouth"))
        self.btnThemes.set_label("_" + _("Themes"))
        self.btnGrub.set_label("_" + _("Grub"))

        self.selectedMenuItem = None
        self.selectedAvailableTheme = None
        self.selectedRemoveTheme = None
        self.threadPackage = None
        self.queue = Queue()
        self.noPlymouth = _('None: no plymouth splash')

        # Set some variables
        self.logFile = '/var/log/dpm.log'
        self.log = Logger(self.logFile, addLogTime=False, maxSizeKB=1024)
        self.version = utils.getPackageVersion('debian-plymouth-manager')
        self.plymouth = Plymouth(self.log)
        self.grub = Grub(self.log)
        self.resolutions = utils.getResolutions('800x600', '', True, False)
        self.currentResolution = self.plymouth.getCurrentResolution()
        self.selectedResolution = self.currentResolution
        self.currentGrubResolution = self.grub.getCurrentResolution()
        self.selectedGrubResolution = self.currentGrubResolution
        self.currentTheme = self.plymouth.getCurrentTheme()
        self.selectedTheme = self.currentTheme
        self.installedThemes = self.plymouth.getInstalledThemes()
        self.availableThemes = self.plymouth.getAvailableThemes()
        self.tv1Handler = TreeViewHandler(self.tv1, self.log)
        self.tv2Handler = TreeViewHandler(self.tv2, self.log)

        self.on_btnPlymouth_clicked()

        # Connect builder signals and show window
        self.builder.connect_signals(self)
        self.window.show_all()

        # TODO: Hide the tool bar for now
        go('tlbMain').set_visible(False)

    # ===============================================
    # Menu section functions
    # ===============================================

    def on_btnPlymouth_clicked(self, widget=None, event=None, refresh=False):
        if self.selectedMenuItem != menuItems[0] or refresh:
            self.selectedMenuItem = menuItems[0]

            # Clear treeviews
            self.tv1Handler.clearTreeView()
            self.tv2Handler.clearTreeView()

            # Set object properties
            self.btn1.set_label(_("Set Plymouth Theme"))
            self.btn2.set_label(_("Preview"))
            self.btn2.show()
            self.lblTitle2.set_visible(True)
            self.sw2.show()

            # Show Installed Themes
            self.lblTitle1.set_label(_("Installed Themes"))
            # Clone the installedThemes list
            listInst = list(self.installedThemes)
            listInst.append(self.noPlymouth)
            # Get current theme and set setcursor
            ind = -1
            if self.currentTheme:
                try:
                    ind = listInst.index(self.currentTheme)
                except:
                    # Theme is set but removed from system
                    ind = 0
            else:
                ind = len(listInst) - 1

            if len(listInst) > 0:
                self.tv1Handler.fillTreeview(listInst, ['str'], ind, 700)

            # Show Resolutios
            self.lblTitle2.set_label(_("Resolutions"))
            ind = -1
            if self.currentResolution:
                try:
                    ind = self.resolutions.index(self.currentResolution)
                except:
                    ind = 0

            if len(self.resolutions) > 0:
                self.tv2Handler.fillTreeview(self.resolutions, ['str'], ind, 700)

    def on_btnThemes_clicked(self, widget=None, event=None, refresh=False):
        if self.selectedMenuItem != menuItems[1] or refresh:
            self.selectedMenuItem = menuItems[1]

            # Clear treeviews
            self.tv1Handler.clearTreeView()
            self.tv2Handler.clearTreeView()

            # Set object properties
            self.btn1.set_label(_("Install Theme"))
            self.btn2.set_label(_("Remove Theme"))
            self.btn2.show()
            self.lblTitle2.set_visible(True)
            self.sw2.show()

            # Show Available Themes
            self.lblTitle1.set_label(_("Available Themes"))
            if len(self.availableThemes) > 0:
                self.tv1Handler.fillTreeview(self.availableThemes, ['str'], 0)

            # Show Installed Themes
            self.lblTitle2.set_label(_("Installed Themes"))
            if len(self.installedThemes) > 0:
                self.tv2Handler.fillTreeview(self.installedThemes, ['str'], 0)

    def on_btnGrub_clicked(self, widget=None, event=None, refresh=False):
        if self.selectedMenuItem != menuItems[2] or refresh:
            self.selectedMenuItem = menuItems[2]

            # Clear treeviews
            self.tv1Handler.clearTreeView()
            self.tv2Handler.clearTreeView()

            # Set object properties
            self.btn1.set_label(_("Set Grub Resolution"))
            self.btn2.hide()
            self.lblTitle2.set_visible(False)
            self.sw2.hide()

            # Show Resolutios
            self.lblTitle1.set_text(_("Grub Resolutions"))
            ind = -1
            if self.currentGrubResolution:
                try:
                    ind = self.resolutions.index(self.currentGrubResolution)
                except:
                    ind = 0

            if len(self.resolutions) > 0:
                self.tv1Handler.fillTreeview(self.resolutions, ['str'], ind, 700)

    # ===============================================
    # Treeview functions
    # ===============================================

    def on_tv1_cursor_changed(self, widget):
        if self.selectedMenuItem == menuItems[0]:
            # Themes Menu
            self.selectedTheme = self.tv1Handler.getSelectedValue()
            self.log.write("Themes menu - seleceted theme: %(theme)s" % { "theme": self.selectedTheme }, 'dpm.tv1Changed')
        elif self.selectedMenuItem == menuItems[1]:
            # Install Menu
            self.selectedAvailableTheme = self.tv1Handler.getSelectedValue()
            self.log.write("Install menu - seleceted available theme: %(theme)s" % { "theme": self.selectedAvailableTheme }, 'dpm.tv1Changed')
        elif self.selectedMenuItem == menuItems[2]:
            # Grub Menu
            self.selectedGrubResolution = self.tv1Handler.getSelectedValue()
            self.log.write("Grub menu - seleceted grub resolution: %(res)s" % { "res": self.selectedGrubResolution }, 'dpm.tv1Changed')

    def on_tv2_cursor_changed(self, widget):
        if self.selectedMenuItem == menuItems[0]:
            # Themes Menu
            self.selectedResolution = self.tv2Handler.getSelectedValue()
            self.log.write("Themes menu - seleceted resolution: %(res)s" % { "res": self.selectedResolution }, 'dpm.tv2Changed')
        elif self.selectedMenuItem == menuItems[1]:
            # Install Menu
            self.selectedRemoveTheme = self.tv2Handler.getSelectedValue()
            self.log.write("Install menu - seleceted theme to remove: %(theme)s" % { "theme": self.selectedRemoveTheme }, 'dpm.tv2Changed')

    # ===============================================
    # Button functions
    # ===============================================

    def on_btn1_clicked(self, widget):
        if self.selectedMenuItem == menuItems[0]:
            # Themes
            self.setTheme()
        elif self.selectedMenuItem == menuItems[1]:
            # Install
            self.installTheme()
        elif self.selectedMenuItem == menuItems[2]:
            # Grub
            self.setGrubResolution()

    def on_btn2_clicked(self, widget):
        if self.selectedMenuItem == menuItems[0]:
            # Themes
            self.preview()
        elif self.selectedMenuItem == menuItems[1]:
            # Install
            self.removeTheme()
        elif self.selectedMenuItem == menuItems[2]:
            # Grub
            pass

    # ===============================================
    # Themes section functions
    # ===============================================

    def preview(self):
        # Check if the selected have been saved
        if self.currentTheme == self.selectedTheme and self.currentResolution == self.selectedResolution:
            self.plymouth.previewPlymouth()
        else:
            title = _("Preview")
            msg = _("You must save before you can preview:\n\nTheme: %(theme)s\nResolution: %(res)s") % { "theme": self.selectedTheme, "res": self.selectedResolution }
            MessageDialogSafe(title, msg, Gtk.MessageType.INFO, self.window).show()

    def setTheme(self):
        self.toggleGuiElements(True)
        if self.selectedTheme != self.noPlymouth:
            if self.selectedResolution is None:
                self.selectedResolution = self.tv2Handler.getValue(self.tv2Handler.getRowCount() - 1)
        else:
            self.selectedTheme = None
            self.selectedResolution = None
        self.log.write(_("Save setting: %(theme)s (%(res)s)") % { "theme": self.selectedTheme, "res": self.selectedResolution }, 'dpm.setTheme', 'info')
        # Start saving in a separate thread
        t = PlymouthSave(self.log, self.selectedTheme, self.selectedResolution)
        t.start()
        GLib.timeout_add(250, self.checkSaveThread)

    def checkSaveThread(self):
        #print 'Thread count = ' + str(threading.active_count())
        # As long there's a thread active, keep spinning
        if threading.active_count() > 1:
            self.pbDPM.pulse()
            return True

        # Get the new data
        self.pbDPM.set_fraction(0)
        self.currentTheme = self.plymouth.getCurrentTheme()
        self.currentResolution = None
        if self.currentTheme != self.noPlymouth:
            self.currentResolution = self.plymouth.getCurrentResolution()
        self.installedThemes = self.plymouth.getInstalledThemes()
        self.availableThemes = self.plymouth.getAvailableThemes()
        if self.selectedMenuItem == menuItems[0]:
            self.on_btnPlymouth_clicked(None, None, True)

        # Thread is done: make button sensitive again
        self.toggleGuiElements(False)
        self.log.write(_("Done saving settings: %(theme)s (%(res)s)") % { "theme": self.currentTheme, "res": self.currentResolution }, 'dpm.checkSaveThread', 'info')

        title = _("Save settings")
        msg = _("Theme: %(theme)s\nResolution: %(res)s\n\nDone") % { "theme": self.currentTheme, "res": str(self.currentResolution) }
        self.log.write(msg, 'dpm.checkSaveThread')
        MessageDialogSafe(title, msg, Gtk.MessageType.INFO, self.window).show()
        return False

    def toggleGuiElements(self, startSave):
        if startSave:
            self.btn1.set_sensitive(False)
            self.btn2.set_sensitive(False)
        else:
            self.btn1.set_sensitive(True)
            self.btn2.set_sensitive(True)

    # ===============================================
    # Install section functions
    # ===============================================

    def installTheme(self):
        self.threadAction = _("install")
        self.threadPackage = self.plymouth.getPackageName(self.selectedAvailableTheme)
        if self.threadPackage:
            dialog = QuestionDialog(_("Install theme"), _("Continue installing theme:\n%(theme)s") % { "theme": self.threadPackage }, self.window)
            go = dialog.show()
            if (go):
                self.toggleGuiElements(True)
                self.log.write(_("Start installing theme: %(theme)s") % { "theme": self.threadPackage }, 'dpm.installTheme', 'info')

                #  Start apt in a separate thread
                cmd = 'apt-get install -y --force-yes %s' % self.threadPackage
                t = ExecuteApt(self.log, cmd, self.queue)
                t.daemon = True
                t.start()
                self.queue.join()

                #self.log.write("Check every 250 miliseconds if thread is still active", 'dpm.installTheme')
                GLib.timeout_add(250, self.checkAptThread)
            else:
                self.log.write(_("User cancel install theme: %(theme)s") % { "theme": self.threadPackage }, 'dpm.installTheme', 'info')
        else:
            title = _("%(act1)s%(act2)s theme") % { "act1": self.threadAction[0].capitalize(), "act2": self.threadAction[1:] }
            msg = _("The package cannot be installed: %(pck)s\nTry apt instead") % { "pck": self.threadPackage }
            self.log.write(msg, 'dpm.installTheme')
            MessageDialogSafe(title, msg, Gtk.MessageType.INFO, self.window).show()

    def removeTheme(self):
        self.threadAction = _("remove")
        self.threadPackage = self.plymouth.getRemovablePackageName(self.selectedRemoveTheme)
        if self.threadPackage:
            dialog = QuestionDialog(_("Remove theme"), _("Continue removing theme:\n%(theme)s") % { "theme": self.threadPackage }, self.window)
            go = dialog.show()
            if (go):
                self.toggleGuiElements(True)

                # Start apt in a separate thread
                self.log.write(_("Start removing theme: %(theme)s") % { "theme": self.threadPackage }, 'dpm.removeTheme', 'info')
                cmd = 'apt-get purge -y --force-yes %s' % self.threadPackage
                t = ExecuteApt(self.log, cmd, self.queue)
                t.daemon = True
                t.start()
                self.queue.join()

                #self.log.write("Check every 250 miliseconds if thread is still active", 'dpm.removeTheme')
                GLib.timeout_add(250, self.checkAptThread)
            else:
                self.log.write(_("User cancel remove theme: %(theme)s") % { "theme": self.threadPackage }, 'dpm.removeTheme', 'info')
        else:
            title = _("%(act1)s%(act2)s theme") % { "act1": self.threadAction[0].capitalize(), "act2": self.threadAction[1:] }
            msg = _("The package cannot be removed: %(pck)s\nIt is part of a meta package.\nTry apt instead") % { "pck": self.selectedRemoveTheme }
            self.log.write(msg, 'dpm.removeTheme')
            MessageDialogSafe(title, msg, Gtk.MessageType.INFO, self.window).show()

    def checkAptThread(self):
        # As long there's a thread active, keep spinning
        if threading.active_count() > 1:
            self.pbDPM.pulse()
            return True

        # Thread is done
        self.pbDPM.set_fraction(0)

        # Get the error data from the queue
        aptError = self.queue.get()

        # Get the new data
        self.installedThemes = self.plymouth.getInstalledThemes()
        self.availableThemes = self.plymouth.getAvailableThemes()
        if self.selectedMenuItem == menuItems[1]:
            self.on_btnThemes_clicked(None, None, True)

        self.toggleGuiElements(False)
        title = _("%(act1)s%(act2)s theme") % { "act1": self.threadAction[0].capitalize(), "act2": self.threadAction[1:] }
        if aptError:
            msg = _("Could not %(action)s theme:\n%(theme)s\nTry apt instead.\n\nError message:\n%(err)s") % { "action": self.threadAction, "theme": self.threadPackage, "err": aptError }
        else:
            msg = _("%(action)s successfully of:\n%(pck)s") % { "action": self.threadAction[0].capitalize() + self.threadAction[1:], "pck": self.threadPackage }

        self.log.write(msg, 'dpm.checkAptThread')
        MessageDialogSafe(title, msg, Gtk.MessageType.INFO, self.window).show()
        return False

    # ===============================================
    # Grub section functions
    # ===============================================

    def setGrubResolution(self):
        self.toggleGuiElements(True)
        self.log.write(_("Save grub resolution: %(res)s") % { "res": self.selectedGrubResolution }, 'dpm.setGrubResolution', 'info')
        # Start saving in a separate thread
        t = GrubSave(self.log, self.selectedGrubResolution)
        t.start()
        GLib.timeout_add(250, self.checkGrubThread)

    def checkGrubThread(self):
        # As long there's a thread active, keep spinning
        if threading.active_count() > 1:
            self.pbDPM.pulse()
            return True

        # Thread is done
        self.pbDPM.set_fraction(0)
        self.currentGrubResolution = self.grub.getCurrentResolution()
        if self.selectedMenuItem == menuItems[2]:
            self.on_btnGrub_clicked(None, None, True)

        self.toggleGuiElements(False)
        title = _("Grub resolution")
        msg = _("Grub resolution saved: %(res)s") % { "res": self.selectedGrubResolution }
        self.log.write(msg, 'dpm.setGrubResolution', 'info')
        MessageDialogSafe(title, msg, Gtk.MessageType.INFO, self.window).show()
        return False

    def on_dpmWindow_destroy(self, widget, data=None):
        # Close the app
        Gtk.main_quit()
