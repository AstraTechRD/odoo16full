from odoo import models, fields


class AvataxExemption(models.Model):
    _name = 'avatax.exemption'
    _description = "Avatax Partner Exemption Codes"
    _rec_names_search = ['name', 'code']

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    description = fields.Char()
    valid_country_ids = fields.Many2many('res.country')
    company_id = fields.Many2one('res.company', required=True)

    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, '[%s] %s' % (record.code, record.name)))
        return res
