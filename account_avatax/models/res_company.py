from datetime import timedelta
from pprint import pformat
import logging

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    avalara_api_id = fields.Char(string='Avalara API ID', groups='base.group_system')
    avalara_api_key = fields.Char(string='Avalara API KEY', groups='base.group_system')
    avalara_environment = fields.Selection(
        string="Avalara Environment",
        selection=[
            ('sandbox', 'Sandbox'),
            ('production', 'Production'),
        ],
        required=True,
        default='sandbox',
    )
    avalara_commit = fields.Boolean(string="Commit in Avatax")
    avalara_address_validation = fields.Boolean(string="Avalara Address Validation")
    avalara_use_upc = fields.Boolean(string="Use UPC", default=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    avalara_api_id = fields.Char(
        related='company_id.avalara_api_id',
        readonly=False,
        string='Avalara API ID',
    )
    avalara_api_key = fields.Char(
        related='company_id.avalara_api_key',
        readonly=False,
        string='Avalara API KEY',
    )
    avalara_partner_code = fields.Char(
        related='company_id.partner_id.avalara_partner_code',
        readonly=False,
        string='Avalara Company Code',
        help="The Avalara Company Code for this company. Avalara will interpret as DEFAULT if it"
             " is not set.",
    )
    avalara_environment = fields.Selection(
        related='company_id.avalara_environment',
        readonly=False,
        string="Avalara Environment",
        required=True,
    )
    avalara_commit = fields.Boolean(
        related='company_id.avalara_commit',
        readonly=False,
        string='Commit in Avatax',
        help="The transactions will be committed for reporting in Avatax.",
    )
    avalara_address_validation = fields.Boolean(
        related='company_id.avalara_address_validation',
        string='Avalara Address Validation',
        readonly=False,
        help="Validate and correct the addresses of partners in North America with Avalara.",
    )
    avalara_use_upc = fields.Boolean(
        related='company_id.avalara_use_upc',
        readonly=False,
        string="Use UPC",
        help="Use Universal Product Code instead of custom defined codes in Avalara.",
    )

    def avatax_sync_company_params(self):
        """Sync all the (supported) parameters that can be configured in Avatax."""
        def get_countries(code_list):
            uncached = set(code_list) - set(country_cache)
            if uncached:
                country_cache.update({
                    country.code: country.id
                    for country in self.env['res.country'].search([('code', 'in', tuple(uncached))])
                })
            return self.env['res.country'].browse([country_cache[code] for code in code_list])
        country_cache = {'*': False}

        # Fetch and create the exemption codes
        existing = {
            exempt['code'] for exempt in self.env['avatax.exemption'].search_read(
                domain=[('company_id', '=', self.company_id.id)],
                fields=['code'],
            )
        }
        client = self.env['account.avatax']._get_client(self.company_id)
        response = client.list_entity_use_codes()
        error = self.env['account.avatax']._handle_response(response, _(
            "Odoo could not fetch the exemption codes of %(company)s",
            company=self.company_id.display_name,
        ))
        if error:
            raise UserError(error)
        self.env['avatax.exemption'].create([
            {
                'code': vals['code'],
                'description': vals['description'],
                'name': vals['name'],
                'valid_country_ids': [(6, 0, get_countries(vals['validCountries']).ids)],
                'company_id': self.company_id.id,
            }
            for vals in response['value']
            if vals['code'] not in existing
        ])
        return True

    def avatax_ping(self):
        """Test the connexion and the credentials."""
        client = self.env['account.avatax']._get_client(self.company_id)
        query_result = client.ping()
        raise UserError(_(
            "Server Response:\n%s",
            pformat(query_result)
        ))

    def avatax_log(self):
        """Start logging all requests done to Avatax, for 30 minutes."""
        self.env['ir.config_parameter'].sudo().set_param(
            'account_avatax.log.end.date',
            (fields.Datetime.now() + timedelta(minutes=30)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        )
        return True
