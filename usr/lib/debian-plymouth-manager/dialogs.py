#!/usr/bin/env python

try:
    import gtk
except Exception, detail:
    print detail

# Show message dialog
# Usage:
# MessageDialog(_("My Title"), "Your (error) message here", gtk.MESSAGE_ERROR).show()
# Message types:
# gtk.MESSAGE_INFO
# gtk.MESSAGE_WARNING
# gtk.MESSAGE_ERROR
class MessageDialog(object):

    def __init__(self, title, message, style):
        self.title = title
        self.message = message
        self.style = style

    ''' Show me on screen '''
    def show(self):
        dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, self.style, gtk.BUTTONS_OK, self.message)
        dialog.set_title(self.title)
        dialog.set_position(gtk.WIN_POS_CENTER)
        dialog.set_icon_from_file("/usr/share/debian-plymouth-manager/icon.png")
        dialog.run()
        dialog.destroy()


# Create question dialog
# Usage:
# dialog = QuestionDialog(_("My Title"), _("Put your question here?"))
#    if (dialog.show()):
class QuestionDialog(object):
    def __init__(self, title, message):
        self.title = title
        self.message = message

    ''' Show me on screen '''
    def show(self):
        dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, self.message)
        dialog.set_title(self.title)
        dialog.set_position(gtk.WIN_POS_CENTER)
        dialog.set_icon_from_file("/usr/share/debian-plymouth-manager/icon.png")
        answer = dialog.run()
        if answer==gtk.RESPONSE_YES:
            return_value = True
        else:
            return_value = False
        dialog.destroy()
        return return_value