# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import encodebytes

from odoo import fields, models
from odoo.modules.module import get_resource_path
from odoo.tools.misc import file_open

class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_default_referral_background(self):
        image_path = get_resource_path('hr_referral', 'static/src/img', 'bg.jpg')
        return encodebytes(file_open(image_path, 'rb').read())

    hr_referral_background = fields.Image(string='Referral Background', default=_get_default_referral_background, required=True)

    def write(self, vals):
        if 'hr_referral_background' in vals:
            self.env["ir.config_parameter"].sudo().set_param('hr_referral.show_grass', str(not bool(vals['hr_referral_background'])))
            if not vals['hr_referral_background']:
                vals['hr_referral_background'] = self._get_default_referral_background()
        return super().write(vals)

    def _init_default_background(self):
        if not self:
            return
        self.hr_referral_background = self._get_default_referral_background()
        self.env["ir.config_parameter"].sudo().set_param('hr_referral.show_grass', True)
