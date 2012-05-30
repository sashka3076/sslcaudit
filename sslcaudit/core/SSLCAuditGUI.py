''' ----------------------------------------------------------------------
SSLCAUDIT - a tool for automating security audit of SSL clients
Released under terms of GPLv3, see COPYING.TXT
Copyright (C) 2012 Alexandre Bezroutchko abb@gremwell.com
---------------------------------------------------------------------- '''

import sys, logging

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from sslcaudit.core.BaseClientAuditController import BaseClientAuditController, HOST_ADDR_ANY
from sslcaudit.core.ClientConnectionAuditEvent import ClientConnectionAuditResult, ClientAuditStartEvent

import SSLCAuditGUIGenerated

logger = logging.getLogger('SSLCAuditGUI')

class SSLCAuditGUI(object):
  def __init__(self, options, file_bag):
    '''
    Initialize UI. Dictionary 'options' comes from SSLCAuditUI.parse_options().
    '''
    self.options = options

    self.app = QApplication(sys.argv)
    self.window = SSLCAuditGUIWindow(self.options, file_bag)

  def run(self):
    self.window.show()
    
    return self.app.exec_()


class SSLCAuditThreadedInterface(QObject):
  '''
  This class is a bridge between PyQt GUI and the core of sslcaudit.
  The main window contains an instance of this class and uses it to communicate with the core.
  It invokes start(), stop(), isRunning() methods of the core to control it.
  It uses sendLog, sendError, sendConnection signals to receive events from the core.
  '''
  sendLog = pyqtSignal(str)
  sendError = pyqtSignal(str)
  sendClientConnectionAuditStart = pyqtSignal(ClientConnectionAuditResult)
  sendClientAuditStartEvent = pyqtSignal(ClientAuditStartEvent)

  def __init__(self, file_bag):
    QObject.__init__(self)
    self.file_bag = file_bag
    self.is_running = False

  def init_controller(self, options):
    self.options = options
    self.controller = BaseClientAuditController(self.options, self.file_bag, event_handler=self.event_handler)

  def start(self):
    try:
      self.controller.start()
      self.is_running = True
    except:
      self.sendError.emit(str(sys.exc_info()[1]))

  def stop(self):
    self.controller.stop()
    self.is_running = False

  def isRunning(self):
    return self.is_running

  def event_handler(self, response):
    '''
    This method gets invoked asynchronously by BaseClientAuditController thread
    '''
    if isinstance(response, ClientConnectionAuditResult):
      self.sendClientConnectionAuditResult.emit(response)


class SSLCAuditGUIWindow(QMainWindow):
  def __init__(self, options, file_bag, parent=None):
    '''
    Initialize UI. Dictionary 'options' comes from SSLCAuditUI.parse_options().
    '''
    QMainWindow.__init__(self, parent)
    
    self.options = options
    self.file_bag = file_bag
    self.settings = QSettings('SSLCAudit')
    self.controller = SSLCAuditThreadedInterface(file_bag)
    
    self.controller.sendLog.connect(self.controllerSentLog)
    #self.controller.sendError.connect(self.controllerSentError)
    #self.controller.sendConnection.connect(self.controllerSentConnection)
    
    # Initialize the UI and store it within the self.ui variable
    self.ui = SSLCAuditGUIGenerated.Ui_MainWindow()
    self.ui.setupUi(self)
    
    # Remove focus from the input box. We need the placeholder text.
    self.setFocus()
    
    # Gives the "Start" button an icon.
    self.ui.startButton.setIcon(QIcon.fromTheme('media-playback-start'))
    
    # Gives the "Copy to Cliboard" button an icon.
    self.ui.copyToClipboardButton.setIcon(QIcon.fromTheme('edit-copy'))
    
    # Gives each of the "Browse" buttons an icon and set their appropriate actions
    for control in [
      self.ui.certificateBrowse1,
      self.ui.certificateBrowse2,
      self.ui.keyBrowse1,
      self.ui.keyBrowse2
    ]:
      control.setIcon(QIcon.fromTheme('document-open'))
      self.connect(control, SIGNAL('clicked()'), lambda control=control: self.browseButtonClicked(control.objectName()))
    
    # Validates the port box via an integer validator
    port_validator = QIntValidator(self)
    port_validator.setRange(0, 65535)
    self.ui.portLineEdit.setValidator(port_validator)
    
    # Sets the check state of every item in both QListWidgets. This is
    # needed for the checkboxes to appear, so add the ciphers and
    # protocols via Qt Designer.
    for item in self.childIterator(self.ui.protocolList) + self.childIterator(self.ui.cipherList):
      item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
      item.setCheckState(Qt.Checked)

    self.ui.showDebugMessagesCheckBox.stateChanged.connect(self.changeDebugMessageVisibility)
    
  def childIterator(self, element):
    return [element.item(i) for i in range(element.count())]
  
  def sendError(self, message):
    QMessageBox.critical(self, 'SSLCAudit', message, QMessageBox.Ok, QMessageBox.Ok)
  
  def controllerSentLog(self, message):
    message = QListWidgetItem(message)
    message.setToolTip('Debug message')

    self.ui.testLog.addItem(message)
    
    if self.ui.showDebugMessagesCheckBox.checkState() != Qt.Checked:
      message.setHidden(True)

  def changeDebugMessageVisibility(self):
    for item in self.childIterator(self.ui.testLog):
      if str(item.toolTip()) == 'Debug message':
        item.setHidden(self.ui.showDebugMessagesCheckBox.checkState() != Qt.Checked)
  
  @pyqtSlot(name='on_copyToClipboardButton_clicked')
  def copyReportToClipboard(self):
    QApplication.clipboard().setText(self.ui.reportText.toPlainText())

  @pyqtSlot(name='on_startButton_clicked')
  def startStopAudit(self):
      if self.controller.isRunning():
        self._stopAudit()
      else:
        self._startAudit()

  def _stopAudit(self):
    try:
      self.controller.stop()
      self.ui.startButton.setText('Start')
      self.ui.startButton.setIcon(QIcon.fromTheme('media-playback-start'))
    except:
      self.sendError(str(sys.exc_info()[1]))

  def _startAudit(self):
    self.ui.startButton.setText('Stop')
    self.ui.startButton.setIcon(QIcon.fromTheme('media-playback-stop'))
    
    try:
      port = int(self.ui.portLineEdit.text())
    except:
      port = 8443
    
    self.options.nclients = self.ui.numerOfRoundsSpinBox.value()
    self.options.listen_on = (
      str(self.ui.hostnameLineEdit.text()),
      port
    )
    try:
      self.controller.init_controller(self.options)
      self.controller.start()
    except:
      self.sendError(str(sys.exc_info()[1]))
      
      self.ui.startButton.setText('Start')
      self.ui.startButton.setIcon(QIcon.fromTheme('media-playback-start'))
      
  
  
  
  def closeEvent(self, event):
    if self.controller and self.controller.isRunning():
      if QMessageBox.question(self, 'SSLCAudit', 'An audit is currently running. Do you really want to exit?', QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes:
        self.controller.stop()
        event.accept()
      else:
        event.ignore()
    else:
      event.accept()

  def browseButtonClicked(self, name):
    textbox = getattr(self.ui, str(name).replace('Browse', 'Edit'))
    filename = QFileDialog.getOpenFileName(
      self,
      getattr(self.ui, str(name)).statusTip(),
      self.settings.value('startup/{}'.format(name), QDir.homePath()).toString()
    )
    
    if filename:
      self.settings.setValue('startup/{}'.format(name), filename)
      textbox.setText(filename)