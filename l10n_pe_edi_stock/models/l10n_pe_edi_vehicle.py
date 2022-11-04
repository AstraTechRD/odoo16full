# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.osv import expression


class L10nPeEdiVehicle(models.Model):
    _name = 'l10n_pe_edi.vehicle'
    _description = 'PE EDI Vehicle'
    _check_company_auto = True

    name = fields.Char(
        string='Vehicle Name',
        required=True)
    license_plate = fields.Char(
        string='License Plate',
        required=True)
    operator_id = fields.Many2one(
        comodel_name='res.partner',
        string='Operator',
        check_company=True,
        help='This value will be used by default in the picking. Define this value when the operator is '
        'always the same for the vehicle.')
    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.company)

    def name_get(self):
        # OVERRIDE
        return [(vehicle.id, "[%s] %s" % (vehicle.license_plate, vehicle.name)) for vehicle in self]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        # OVERRIDE
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            domain = ['|', ('name', 'ilike', name), ('license_plate', 'ilike', name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
