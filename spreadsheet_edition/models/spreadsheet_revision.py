# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models


class SpreadsheetRevision(models.Model):
    _name = "spreadsheet.revision"
    _description = "Collaborative spreadsheet revision"

    active = fields.Boolean(default=True)
    res_model = fields.Char(string="Model", required=True)
    res_id = fields.Many2oneReference(string="Record id", model_field='res_model', required=True)
    commands = fields.Char(required=True)
    revision_id = fields.Char(required=True)
    parent_revision_id = fields.Char(required=True)
    _sql_constraints = [
        ('parent_revision_unique', 'unique(parent_revision_id, res_id, res_model)', 'o-spreadsheet revision refused due to concurrency')
    ]

    @api.autovacuum
    def _gc_revisions(self):
        days = int(self.env["ir.config_parameter"].sudo().get_param(
            "spreadsheet_edition.revisions_limit_days",
            '60',
        ))
        timeout_ago = datetime.datetime.utcnow()-datetime.timedelta(days=days)
        domain = [("create_date", "<", timeout_ago), ("active", "=", False)]
        return self.search(domain).unlink()
