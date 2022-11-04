# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    @api.model
    def _get_random_token(self):
        """Generate a 20 char long pseudo-random string of digits for barcode
        generation.

        A decimal serialisation is longer than a hexadecimal one *but* it
        generates a more compact barcode (Code128C rather than Code128A).

        Generate 8 bytes (64 bits) barcodes as 16 bytes barcodes are not
        compatible with all scanners.
         """
        return str(int.from_bytes(os.urandom(8), 'little'))

    barcode = fields.Char(default=_get_random_token, readonly=True, copy=False, index=True)

    _sql_constraints = [
        ('barcode_event_uniq', 'unique(barcode)', "Barcode should be unique")
    ]

    def _init_column(self, column_name):
        """ to avoid generating a single default barcide when installing the module,
            we need to set the default row by row for this column """
        if column_name == "barcode":
            _logger.debug("Table '%s': setting default value of new column %s to unique values for each row",
                          self._table, column_name)
            self.env.cr.execute("SELECT id FROM %s WHERE barcode IS NULL" % self._table)
            registration_ids = self.env.cr.dictfetchall()
            query_list = [{'id': reg['id'], 'barcode': self._get_random_token()} for reg in registration_ids]
            query = 'UPDATE ' + self._table + ' SET barcode = %(barcode)s WHERE id = %(id)s;'
            self.env.cr._obj.executemany(query, query_list)

        else:
            super(EventRegistration, self)._init_column(column_name)

    @api.model
    def register_attendee(self, barcode, event_id):
        attendee = self.search([('barcode', '=', barcode)], limit=1)
        if not attendee:
            return {'error': 'invalid_ticket'}
        res = attendee._get_registration_summary()
        if attendee.state == 'cancel':
            status = 'canceled_registration'
        elif not attendee.event_id.is_ongoing:
            status = 'not_ongoing_event'
        elif attendee.state != 'done':
            if event_id and attendee.event_id.id != event_id:
                status = 'need_manual_confirmation'
            else:
                attendee.action_set_done()
                status = 'confirmed_registration'
        else:
            status = 'already_registered'
        res.update({'status': status, 'event_id': event_id})
        return res
