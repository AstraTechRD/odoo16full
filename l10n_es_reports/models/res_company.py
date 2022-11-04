# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._create_mod_boe_sequences()
        return companies

    def _create_mod_boe_sequences(self):
        """ Creates two sequences for each element of the record set:
        one for mod 347 BOE, and another one for mod 349 BOE.
        """
        sequence_model = self.env['ir.sequence']
        for record in self:
            sequence_model.create({
                    'name': "Mod 347 BOE sequence for company " + record.name,
                    'code': "l10n_es.boe.mod_347",
                    'padding': 10,
                    'company_id': record.id,
            })
            sequence_model.create({
                    'name': "Mod 349 BOE sequence for company " + record.name,
                    'code': "l10n_es.boe.mod_349",
                    'padding': 10,
                    'company_id': record.id,
            })
