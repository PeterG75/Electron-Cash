import copy
import datetime
import time
from functools import partial
import json
import threading
import sys
from pathlib import Path
from os.path import basename, splitext

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from electroncash.address import Address, PublicKey, Base58Error
from electroncash.bitcoin import *
from electroncash.i18n import _
from electroncash.plugins import run_hook

from .util import *

from electroncash.util import bfh,   NotEnoughFunds, ExcessiveFee, InvalidPassword
from electroncash.transaction import Transaction

from .transaction_dialog import show_transaction

dialogs = []  # Otherwise python randomly garbage collects the dialogs...


class CrowdfundingDialog(QDialog, MessageBoxMixin):

    def __init__(self, parent, file_receiver=None, show_on_create=False, screen_name="Upload Token Document"):
        # We want to be a top-level window
        QDialog.__init__(self, parent)

        # check parent window type
        self.parent = parent
        from .main_window import ElectrumWindow

        self.setWindowTitle(_(screen_name))

        vbox = QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(QLabel("Manage Crowdfunding Transactions"))

        d = WindowModalDialog(self, _('Crowdfunding Transactions'))
        d.setMinimumSize(610, 290)

        layout = QGridLayout(d)

        message_e = QTextEdit()
        layout.addWidget(QLabel(_('Raw Signed Inputs')), 1, 0)
        layout.addWidget(message_e, 1, 1)
        layout.setRowStretch(2,3)

        address_e = QLineEdit()
        #address_e.setText(address.to_ui_string() if address else '')

        address_e.setText("test")
        layout.addWidget(QLabel(_('Destination Address')), 2, 0)
        layout.addWidget(address_e, 2, 1)

        amount_e = QLineEdit()
        layout.addWidget(QLabel(_('Sats Amount')), 3, 0)
        layout.addWidget(amount_e, 3, 1)

        raw_full_tx_e = QTextEdit()
        layout.addWidget(QLabel(_('Raw Full Tx')), 4, 0)
        layout.addWidget(raw_full_tx_e, 4, 1)

        hbox = QHBoxLayout()

        b = QPushButton(_("Sign"))
        b.clicked.connect(lambda: self.do_sign(address_e, message_e, amount_e,raw_full_tx_e))
        hbox.addWidget(b)



        b = QPushButton(_("Close"))
        b.clicked.connect(d.accept)
        hbox.addWidget(b)
        layout.addLayout(hbox, 5, 1)
        d.exec_()


    def do_sign(self,address_e, message_e, amount_e,raw_full_tx_e):

        version = 1
        locktime=0
        tx=Transaction("123")
        _type= 0
        myaddr=Address.from_string(address_e.text())
        myoutput = (_type, myaddr, int(amount_e.text()))
        print ("myoutput is ",myoutput)
        serialized_output=Transaction.serialize_output(tx, myoutput)
        print ("serialized output is ",serialized_output)

        nVersion = int_to_hex(version, 4)
        nLocktime = int_to_hex(locktime, 4)

        inputs = message_e.toPlainText().splitlines()

        txins = var_int(len(inputs)) + ''.join(inputs)

        txouts = var_int(1) + serialized_output
        raw_tx = nVersion + txins + txouts + nLocktime
        print ("the raw tx is ",raw_tx)
        raw_full_tx_e.setText(raw_tx)

    def upload(self):
        if not self.is_dirty:
            self.progress_label.setText("Broadcasting 1 of " + str(len(self.tx_batch)) + " transactions")
            self.progress.setVisible(True)
            self.progress.setMinimum(0)
            self.progress.setMaximum(len(self.tx_batch))
            broadcast_count = 0
            # Broadcast all transaction to the nexwork
            for tx in self.tx_batch:
                tx_desc = None
                status, msg = self.network.broadcast(tx)
                # print(status)
                # print(msg)
                if status == False:
                    self.show_error(msg)
                    self.show_error("Upload failed. Try again.")
                    return

                broadcast_count += 1
                time.sleep(0.1)
                self.progress_label.setText("Broadcasting " + str(broadcast_count) + " of " + str(len(self.tx_batch)) + " transactions")
                self.progress.setValue(broadcast_count)
                QApplication.processEvents()

            self.progress_label.setText("Broadcasting complete.")
            self.progress.setHidden(True)
            try:
                self.parent.token_dochash_e.setText(self.hash.text())
                self.parent.token_url_e.setText(self.bitcoinfileAddr_label.text())
            except AttributeError:
                pass

            self.show_message("File upload complete.")
            self.close()

    def closeEvent(self, event):
        event.accept()
        self.parent.raise_()
        self.parent.activateWindow()
        try:
            dialogs.remove(self)
        except ValueError:
            pass
