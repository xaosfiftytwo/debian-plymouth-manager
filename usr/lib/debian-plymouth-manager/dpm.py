#!/usr/bin/env python -u

try:
    import os
    import sys
    import pygtk
    pygtk.require("2.0")
    import gobject
    import gtk
    import threading
    import glib
    import functions
    from dialogs import QuestionDialog, MessageDialog
    from save import SavePlymouthTheme
    from config import Config
    from execapt import ExecuteApt
except Exception, detail:
    print detail
    sys.exit(1)
    
#class for the main window
class DebianPlymouthManager:
    
    
    conf = Config('dpm.conf')
    version = conf.getValue('Program', 'version')
    currentThemeName = ''
    currentResolution = ''
    selectedThemeName = ''
    selectedResolution = ''
    threadOk = False
    threadAction = ''
    threadPackage = ''
    noPlym = 'None: no plymouth splash'

    def __init__(self):
        # Load window and widgets
        self.builder = gtk.Builder()
        self.builder.add_from_file("/usr/share/debian-plymouth-manager/debian-plymouth-manager-gtk3.glade")
        self.window = self.builder.get_object("ManagerWindow")
        self.tvAvailable = self.builder.get_object("tvAvailable")
        self.tvInstalled = self.builder.get_object("tvInstalled")
        self.tvResolution = self.builder.get_object("tvResolution")
        self.btnInstallTheme = self.builder.get_object("btnInstallTheme")
        self.btnRemoveTheme = self.builder.get_object("btnRemoveTheme")
        self.btnPreviewTheme = self.builder.get_object("btnPreviewTheme")
        self.btnSetTheme = self.builder.get_object("btnSetTheme")
        self.lblSelectedSettings = self.builder.get_object("lblSelectedSettings")
        self.lblCurrentSettings = self.builder.get_object("lblCurrentSettings")
        self.spinner = self.builder.get_object("spinner")
        self.statusbar = self.builder.get_object("statusbar")
        
        # Show version number in status bar
        functions.pushMessage(self.statusbar, self.version)
        
        # Fill screen resolutions treeview
        self.fillResolutions()

        # Fill Installed themes treeview
        self.fillInstalled()

        # Fill available themes treeview
        self.fillAvailable()

        # Show current plymouth settings from grub
        curRes = ''
        if self.currentResolution != '':
            curRes = ' (' + self.currentResolution + ')'
        if self.currentThemeName == '':
            self.currentThemeName = self.selectedThemeName
        self.lblCurrentSettings.set_text(self.currentThemeName + curRes)
        
        selRes = ''
        if self.selectedResolution != '' and self.selectedThemeName != self.noPlym:
            selRes = ' (' + self.selectedResolution + ')'
        self.lblSelectedSettings.set_text(self.selectedThemeName + selRes)
        
        # Add events
        signals = {
            "on_btnInstallTheme_clicked" : self.installTheme,
            "on_btnRemoveTheme_clicked" : self.removeTheme,
            "on_btnPreviewTheme_clicked" : self.previewTheme,
            "on_btnSetTheme_clicked" : self.setTheme,
            "on_tvInstalled_cursor_changed" : self.changeTheme,
            "on_tvResolution_cursor_changed" : self.changeRes,
            "on_eventbox_button_release_event" : self.about,
            "on_ManagerWindow_destroy" : self.destroy
        }
        self.builder.connect_signals(signals)
        
        self.window.show()
        
    def fillResolutions(self):
        listRes = functions.getResolutions('800x600', '1280x1024')
        # Get current resolution and set setcursor
        ind = 0
        curRes = functions.getCurrentResolution()
        if curRes != '':
            try:
                ind = listRes.index(curRes)
            except:
                ind = 0
        else:
            #self.lblCurrentSettings.set_text(self.noPlym)
            ind = len(listRes) - 1
            
        if len(listRes) > 0:
            functions.fillTreeview(self.tvResolution, listRes, ind, 700)
            # Fill resolution settings
            self.selectedResolution = functions.getSelectedValue(self.tvResolution)
            if curRes != '':
                self.currentResolution = curRes
            else:
                self.currentResolution = ''
                

    def fillInstalled(self):
        listInst = functions.getInstalledThemes()
        listInst.append(self.noPlym)
        # Get current theme and set setcursor
        ind = 0
        curTheme = functions.getCurrentTheme()
        if curTheme != '':
            try:
                ind = listInst.index(curTheme)
            except:
                # Theme is set but removed from system
                ind = 0
        else:
            self.selectedThemeName = self.noPlym
            #self.lblCurrentSettings.set_text(self.noPlym)
            ind = len(listInst) - 1
            
        if len(listInst) > 0:
            functions.fillTreeview(self.tvInstalled, listInst, ind, 700)
            # Fill resolution settings
            self.selectedThemeName = functions.getSelectedValue(self.tvInstalled)
            if curTheme != "":
                self.currentThemeName = curTheme
            else:
                self.currentThemeName = ''
            
    def fillAvailable(self):
        listavl = functions.getAvailableThemes()
        functions.fillTreeview(self.tvAvailable, listavl, 0)
    
    def main(self):
        gtk.main()
    
    def destroy(self, widget, data=None):
        gtk.main_quit()
        
    def about(self, widget, event):
        print "About open"
        self.about = self.builder.get_object("About")
        author = 'Author: ' + self.conf.getValue('Program', 'author')
        email = 'E-mail: ' + self.conf.getValue('Program', 'email')
        home = self.conf.getValue('Program', 'home')
        comments = self.conf.getValue('Program', 'comments')
        self.about.set_comments(author + '\n' + email + '\n\n' + comments)
        self.about.set_version(self.version)
        self.about.set_website(home)
        self.about.run()
        self.about.hide()

    def changeTheme(self, widget):
        self.selectedThemeName = functions.getSelectedValue(self.tvInstalled)
        if 'None' in self.selectedThemeName:
            self.selectedResolution = ''
        selRes = ''
        if self.selectedResolution != '':
            selRes = ' (' + self.selectedResolution + ')'
        self.lblSelectedSettings.set_text(self.selectedThemeName + selRes)

    def changeRes(self, widget):
        self.selectedResolution = functions.getSelectedValue(self.tvResolution)
        self.lblSelectedSettings.set_text(self.selectedThemeName + " (" + self.selectedResolution + ")")

    def aptThreadResult(self, ok):
        self.threadOk = ok
    
    def installTheme(self, widget):
        self.threadAction = 'install'
        theme = functions.getSelectedValue(self.tvAvailable)
        self.threadPackage = functions.getPackageName(theme)
        if self.threadPackage != '':
            dialog = QuestionDialog("Install theme", "Continue installing theme:\n" + self.threadPackage)
            go = dialog.show()
            if (go):
                self.toggleGuiElements(True)
                functions.pushMessage(self.statusbar, 'Start installing theme: ' + self.threadPackage)
                #  Start apt in a separate thread
                t = ExecuteApt(self.aptThreadResult)
                cmd = 'apt-get install -y --force-yes ' + self.threadPackage
                t.start(cmd, True, self.statusbar)
                print "Install thread started"
                glib.timeout_add(5, self.checkAptThread)
            else:
                print "User cancel install theme: " + self.threadPackage
        else:
            title = self.threadAction[0].capitalize() + self.threadAction[1:] + ' theme'
            msg = "The package cannot be installed: " + self.threadPackage + "\nTry apt instead"
            print msg
            MessageDialog(title, msg, gtk.MESSAGE_INFO).show()

    def removeTheme(self, widget):
        self.threadAction = 'uninstall'
        self.threadPackage = functions.getRemovablePackageName(self.selectedThemeName)
        if self.threadPackage != '':
            dialog = QuestionDialog("Uninstall theme", "Continue uninstalling theme:\n" + self.threadPackage)
            go = dialog.show()
            if (go):
                self.toggleGuiElements(True)
                #  Start apt in a separate thread
                functions.pushMessage(self.statusbar, 'Start uninstalling theme: ' + self.threadPackage)
                t = ExecuteApt(self.aptThreadResult)
                cmd = 'apt-get purge -y --force-yes ' + self.threadPackage
                t.start(cmd, True, self.statusbar)
                print "Remove thread started"
                glib.timeout_add(5, self.checkAptThread)
            else:
                print "User cancel uninstall theme: " + self.threadPackage
        else:
            title = self.threadAction[0].capitalize() + self.threadAction[1:] + ' theme'
            msg = "The package cannot be uninstalled: " + self.threadPackage + "\nIt is part of a meta package.\nTry apt instead"
            print msg
            MessageDialog(title, msg, gtk.MESSAGE_INFO).show()
            
    def checkAptThread(self):
        print 'Thread count = ' + str(threading.active_count())
        # As long there's a thread active, keep spinning
        if threading.active_count() > 1:
            return True        
        # Thread is done: buttons sensitive again
        self.toggleGuiElements(False)
        msg = "Done " + self.threadAction + "ing package: " + self.threadPackage
        functions.pushMessage(self.statusbar, msg)
        print msg
        title = self.threadAction[0].capitalize() + self.threadAction[1:] + ' theme'
        if self.threadOk:
            msg = "Theme successfully " + self.threadAction + "ed:\n" + self.threadPackage
        else:
            msg = "Could not " + self.threadAction + " theme:\n" + self.threadPackage + "\nTry apt instead."
        
        print msg
        MessageDialog(title, msg , gtk.MESSAGE_INFO).show()
        return False
            
    def previewTheme(self, widget):
        functions.previewPlymouth()
        
    
    def setTheme(self, widget):
        self.toggleGuiElements(True)
        msg = "Save setting: " + self.selectedThemeName + " (" + self.selectedResolution + ")"
        functions.pushMessage(self.statusbar, msg)
        print msg
        # Start saving in a separate thread
        t = SavePlymouthTheme(self.selectedThemeName, self.selectedResolution, self.statusbar)
        t.start()
        # Run spinner as long as the thread is alive
        glib.timeout_add(5, self.checkSaveThread)

    def checkSaveThread(self):
        #print 'Thread count = ' + str(threading.active_count())
        # As long there's a thread active, keep spinning
        if threading.active_count() > 1:
            self.spinner.start()
            return True        
        # Thread is done: stop spinner and make button sensitive again
        self.toggleGuiElements(False)
        # Show message that we're done
        msg = "Done saving settings: " + self.selectedThemeName + " (" + self.selectedResolution + ")"
        functions.pushMessage(self.statusbar, msg)
        print msg
        title = 'Save settings'
        msg = 'Theme: ' + self.selectedThemeName + '\nResolution: ' + self.selectedResolution + '\n\nDone'
        MessageDialog(title, msg , gtk.MESSAGE_INFO).show()
        return False
    
    def toggleGuiElements(self, startSave):
        if startSave:
            self.btnSetTheme.set_sensitive(False)
            self.btnInstallTheme.set_sensitive(False)
            self.btnRemoveTheme.set_sensitive(False)
            self.spinner.show()
        else:
            self.spinner.stop()
            self.spinner.hide()
            self.btnSetTheme.set_sensitive(True)
            self.btnInstallTheme.set_sensitive(True)
            self.btnRemoveTheme.set_sensitive(True)
            # Show current settings
            selRes = ''
            if self.selectedResolution != '':
                selRes = ' (' + self.selectedResolution + ')'
            self.lblCurrentSettings.set_text(self.selectedThemeName + selRes)
            self.lblSelectedSettings.set_text(self.selectedThemeName + selRes)
            self.fillInstalled()
            self.fillAvailable()
            self.fillResolutions()
            


if __name__ == "__main__":
    # Flush print when it's called
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    # Create an instance of our GTK application
    app = DebianPlymouthManager()
    app.main()
