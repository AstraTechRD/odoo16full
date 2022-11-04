# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def login(self, pin=False, set_in_session=True):
        """ Use the session to remember the current employee between views.
        The main purpose is to avoid a hash implementation on client side.
        """
        if not pin:
            pin = False
        if self.pin == pin:
            if set_in_session:
                request.session['employee_id'] = self.id
            return True
        elif not pin and self.id == request.session.get('employee_id', []):
            return True
        return False

    def logout(self, pin=False):
        if not pin:
            pin = False
        if self.pin == pin:
            request.session['employee_id'] = False
            return True
        return False

    def _get_employee_fields_for_tablet(self):
        return [
            'id',
            'name',
            'barcode',
        ]
