# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ctypes
from pathlib import Path
from queue import Queue
from time import sleep

from odoo.addons.hw_drivers.driver import Driver
from odoo.addons.hw_drivers.event_manager import event_manager


easyCTEPPath = Path(__file__).parent.parent / 'lib/ctep/libeasyctep.so'

if easyCTEPPath.exists():
    # Load library
    easyCTEP = ctypes.CDLL(easyCTEPPath)

TERMINAL_ERRORS = {
    '1802': 'Terminal is busy',
    '1803': 'Timeout expired',
    '2629': 'User cancellation',
}

IGNORE_ERRORS = [
    '2630',  # Manually cancelled by cashier, do not show the error
]


class WorldlineDriver(Driver):
    connection_type = 'ctep'

    def __init__(self, identifier, device):
        super(WorldlineDriver, self).__init__(identifier, device)
        self.device_type = 'payment'
        self.device_connection = 'network'
        self.device_name = 'Worldline terminal %s' % self.device_identifier
        self.device_manufacturer = 'Worldline'
        self.actions = Queue()
        self.cid = None
        self.owner = None

        self._actions.update({
            '': self._action_default,
        })

    @classmethod
    def supported(cls, device):
        # All devices with connection_type CTEP are supported
        return True

    def _action_default(self, data):
        if data['messageType'] == 'Transaction':
            self.actions.put({
                'type': 'transaction',
                'action_identifier': data['actionIdentifier'],
                'amount': data['amount'] / 100,
                'reference': data['TransactionID'],
                'cid': data['cid'],
                'owner': self.data['owner'],
            })
        elif data['messageType'] == 'Cancel':
            self.cancelTransaction()
        elif data['messageType'] == 'LastTransactionStatus':
            self.actions.put({
                'type': 'lastTransactionStatus',
            })

    def run(self):
        while True:
            action = self.actions.get()
            if action['type'] == 'transaction':
                self.processTransaction(action)
            elif action['type'] == 'lastTransactionStatus':
                self.lastTransactionStatus()
            # After a payment has been processed, the display on the terminal still shows some
            # information for about 4-5 seconds. No request can be processed during this period.
            sleep(5)

    def processTransaction(self, transaction):
        self.cid = transaction['cid']
        self.owner = transaction['owner']

        if transaction['amount'] <= 0:
            return self.send_status(error='The terminal cannot process negative or null transactions.')

        # Notify transaction start
        self.send_status(stage='WaitingForCard')

        # Transaction
        merchant_receipt = ctypes.create_string_buffer(500)
        customer_receipt = ctypes.create_string_buffer(500)
        card = ctypes.create_string_buffer(20)
        error_code = ctypes.create_string_buffer(10)
        result = easyCTEP.startTransaction(
            ctypes.byref(self.dev),
            ctypes.c_char_p(str(transaction['amount']).encode('utf-8')),
            ctypes.c_char_p(str(transaction['reference']).encode('utf-8')),
            ctypes.c_ulong(transaction['action_identifier']),
            ctypes.byref(merchant_receipt),
            ctypes.byref(customer_receipt),
            ctypes.byref(card),
            ctypes.byref(error_code),
        )

        if result == 1:
            # Transaction successful
            self.send_status(
                response='Approved',
                ticket=customer_receipt.value,
                ticket_merchant=merchant_receipt.value,
                card=card.value,
                transaction_id=transaction['action_identifier'],
            )
        elif result == 0:
            # Transaction failed
            error_code = error_code.value.decode('utf-8')
            if error_code not in IGNORE_ERRORS:
                error_msg = '%s (Error code: %s)' % (TERMINAL_ERRORS.get(error_code, 'Transaction was not processed correctly'), error_code)
                self.send_status(error=error_msg)
        elif result == -1:
            # Terminal disconnection, check status manually
            self.send_status(disconnected=True)

    def cancelTransaction(self):
        error_code = ctypes.create_string_buffer(10)
        result = easyCTEP.abortTransaction(ctypes.byref(self.dev), ctypes.byref(error_code))

        if result:
            self.send_status(stage='Cancel')
        else:
            error_code = error_code.value.decode('utf-8')
            error_msg = '%s (Error code: %s)' % (TERMINAL_ERRORS.get(error_code, 'Transaction could not be cancelled'), error_code)
            self.send_status(stage='Cancel', error=error_msg)

    def lastTransactionStatus(self):
        action_identifier = ctypes.c_ulong()
        amount = ctypes.c_double()
        time = ctypes.create_string_buffer(20)
        error_code = ctypes.create_string_buffer(10)
        result = easyCTEP.lastTransactionStatus(ctypes.byref(self.dev), ctypes.byref(action_identifier), ctypes.byref(amount), ctypes.byref(time), ctypes.byref(error_code))

        if result:
            self.send_status(value={
                'action_identifier': action_identifier.value,
                'amount': amount.value,
                'time': time.value,
            })
        else:
            error_code = error_code.value.decode('utf-8')
            error_msg = '%s (Error code: %s)' % (TERMINAL_ERRORS.get(error_code, 'Transaction was not processed correctly'), error_code)
            self.send_status(value={
                'error': error_msg,
            })

    def send_status(self, value='', response=False, stage=False, ticket=False, ticket_merchant=False, card=False, transaction_id=False, error=False, disconnected=False):
        self.data = {
            'value': value,
            'Stage': stage,
            'Response': response,
            'Ticket': ticket,
            'TicketMerchant': ticket_merchant,
            'Card': card,
            'PaymentTransactionID': transaction_id,
            'Error': error,
            'Disconnected': disconnected,
            'owner': self.owner or self.data['owner'],
            'cid': self.cid,
        }
        event_manager.device_changed(self)
