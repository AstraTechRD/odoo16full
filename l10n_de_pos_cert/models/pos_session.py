# -*- coding: utf-8 -*-

from odoo import models, fields, _, release
from odoo.tools.float_utils import float_repr
from odoo.exceptions import UserError
import ast
import uuid

COUNTRY_CODE_MAP = {
    "BD": "BGD", "BE": "BEL", "BF": "BFA", "BG": "BGR", "BA": "BIH", "BB": "BRB", "WF": "WLF", "BL": "BLM", "BM": "BMU",
    "BN": "BRN", "BO": "BOL", "BH": "BHR", "BI": "BDI", "BJ": "BEN", "BT": "BTN", "JM": "JAM", "BV": "BVT", "BW": "BWA",
    "WS": "WSM", "BQ": "BES", "BR": "BRA", "BS": "BHS", "JE": "JEY", "BY": "BLR", "BZ": "BLZ", "RU": "RUS", "RW": "RWA",
    "RS": "SRB", "TL": "TLS", "RE": "REU", "TM": "TKM", "TJ": "TJK", "RO": "ROU", "TK": "TKL", "GW": "GNB", "GU": "GUM",
    "GT": "GTM", "GS": "SGS", "GR": "GRC", "GQ": "GNQ", "GP": "GLP", "JP": "JPN", "GY": "GUY", "GG": "GGY", "GF": "GUF",
    "GE": "GEO", "GD": "GRD", "GB": "GBR", "GA": "GAB", "SV": "SLV", "GN": "GIN", "GM": "GMB", "GL": "GRL", "GI": "GIB",
    "GH": "GHA", "OM": "OMN", "TN": "TUN", "JO": "JOR", "HR": "HRV", "HT": "HTI", "HU": "HUN", "HK": "HKG", "HN": "HND",
    "HM": "HMD", "VE": "VEN", "PR": "PRI", "PS": "PSE", "PW": "PLW", "PT": "PRT", "SJ": "SJM", "PY": "PRY", "IQ": "IRQ",
    "PA": "PAN", "PF": "PYF", "PG": "PNG", "PE": "PER", "PK": "PAK", "PH": "PHL", "PN": "PCN", "PL": "POL", "PM": "SPM",
    "ZM": "ZMB", "EH": "ESH", "EE": "EST", "EG": "EGY", "ZA": "ZAF", "EC": "ECU", "IT": "ITA", "VN": "VNM", "SB": "SLB",
    "ET": "ETH", "SO": "SOM", "ZW": "ZWE", "SA": "SAU", "ES": "ESP", "ER": "ERI", "ME": "MNE", "MD": "MDA", "MG": "MDG",
    "MF": "MAF", "MA": "MAR", "MC": "MCO", "UZ": "UZB", "MM": "MMR", "ML": "MLI", "MO": "MAC", "MN": "MNG", "MH": "MHL",
    "MK": "MKD", "MU": "MUS", "MT": "MLT", "MW": "MWI", "MV": "MDV", "MQ": "MTQ", "MP": "MNP", "MS": "MSR", "MR": "MRT",
    "IM": "IMN", "UG": "UGA", "TZ": "TZA", "MY": "MYS", "MX": "MEX", "IL": "ISR", "FR": "FRA", "IO": "IOT", "SH": "SHN",
    "FI": "FIN", "FJ": "FJI", "FK": "FLK", "FM": "FSM", "FO": "FRO", "NI": "NIC", "NL": "NLD", "NO": "NOR", "NA": "NAM",
    "VU": "VUT", "NC": "NCL", "NE": "NER", "NF": "NFK", "NG": "NGA", "NZ": "NZL", "NP": "NPL", "NR": "NRU", "NU": "NIU",
    "CK": "COK", "XK": "XKX", "CI": "CIV", "CH": "CHE", "CO": "COL", "CN": "CHN", "CM": "CMR", "CL": "CHL", "CC": "CCK",
    "CA": "CAN", "CG": "COG", "CF": "CAF", "CD": "COD", "CZ": "CZE", "CY": "CYP", "CX": "CXR", "CR": "CRI", "CW": "CUW",
    "CV": "CPV", "CU": "CUB", "SZ": "SWZ", "SY": "SYR", "SX": "SXM", "KG": "KGZ", "KE": "KEN", "SS": "SSD", "SR": "SUR",
    "KI": "KIR", "KH": "KHM", "KN": "KNA", "KM": "COM", "ST": "STP", "SK": "SVK", "KR": "KOR", "SI": "SVN", "KP": "PRK",
    "KW": "KWT", "SN": "SEN", "SM": "SMR", "SL": "SLE", "SC": "SYC", "KZ": "KAZ", "KY": "CYM", "SG": "SGP", "SE": "SWE",
    "SD": "SDN", "DO": "DOM", "DM": "DMA", "DJ": "DJI", "DK": "DNK", "VG": "VGB", "DE": "DEU", "YE": "YEM", "DZ": "DZA",
    "US": "USA", "UY": "URY", "YT": "MYT", "UM": "UMI", "LB": "LBN", "LC": "LCA", "LA": "LAO", "TV": "TUV", "TW": "TWN",
    "TT": "TTO", "TR": "TUR", "LK": "LKA", "LI": "LIE", "LV": "LVA", "TO": "TON", "LT": "LTU", "LU": "LUX", "LR": "LBR",
    "LS": "LSO", "TH": "THA", "TF": "ATF", "TG": "TGO", "TD": "TCD", "TC": "TCA", "LY": "LBY", "VA": "VAT", "VC": "VCT",
    "AE": "ARE", "AD": "AND", "AG": "ATG", "AF": "AFG", "AI": "AIA", "VI": "VIR", "IS": "ISL", "IR": "IRN", "AM": "ARM",
    "AL": "ALB", "AO": "AGO", "AQ": "ATA", "AS": "ASM", "AR": "ARG", "AU": "AUS", "AT": "AUT", "AW": "ABW", "IN": "IND",
    "AX": "ALA", "AZ": "AZE", "IE": "IRL", "ID": "IDN", "UA": "UKR", "QA": "QAT", "MZ": "MOZ"
}


class PosSession(models.Model):
    _inherit = 'pos.session'
    l10n_de_fiskaly_cash_point_closing_uuid = fields.Char(string="Fiskaly Cash Point Closing Uuid", readonly=True,
        help="The uuid of the 'cash point closing' created at Fiskaly when closing the session.")

    def _validate_session(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        res = super()._validate_session(balancing_account, amount_to_balance, bank_payment_method_diffs)
        orders = self.order_ids.filtered(lambda o: o.state in ['done', 'invoiced'])
        # We don't want to block the user that need to validate his session order in order to create his TSS
        if self.config_id.is_company_country_germany and self.config_id.l10n_de_fiskaly_tss_id and self.order_ids:
            orders = orders.sorted('l10n_de_fiskaly_time_end')
            json = self._l10n_de_create_cash_point_closing_json(orders)
            self._l10n_de_send_fiskaly_cash_point_closing(json)

        return res

    def _l10n_de_create_cash_point_closing_json(self, orders):
        vat_definitions = self._l10n_de_fiskaly_get_vat_definitions()

        self.env.cr.execute("""
            SELECT pm.is_cash_count, sum(p.amount) AS amount
            FROM pos_payment p
                LEFT JOIN pos_payment_method pm ON p.payment_method_id=pm.id
                JOIN account_journal journal ON pm.journal_id=journal.id
            WHERE p.session_id=%s AND journal.type IN ('cash', 'bank')
            GROUP BY pm.is_cash_count 
        """, [self.id])
        total_payment_result = self.env.cr.dictfetchall()

        total_cash = 0
        total_bank = 0
        for payment in total_payment_result:
            if payment['is_cash_count']:
                total_cash = payment['amount']
            else:
                total_bank = payment['amount']

        self.env.cr.execute("""
            SELECT account_tax.amount, 
                   sum(pos_order_line.price_subtotal) as excl_vat, 
                   sum(pos_order_line.price_subtotal_incl) as incl_vat 
            FROM pos_order 
            JOIN pos_order_line ON pos_order.id=pos_order_line.order_id 
            JOIN account_tax_pos_order_line_rel ON account_tax_pos_order_line_rel.pos_order_line_id=pos_order_line.id 
            JOIN account_tax ON account_tax_pos_order_line_rel.account_tax_id=account_tax.id
            WHERE pos_order.session_id=%s 
            GROUP BY account_tax.amount
        """, [self.id])

        amounts_per_vat_id_result = self.env.cr.dictfetchall()

        json = self.env['ir.qweb']._render('l10n_de_pos_cert.dsfinvk_cash_point_closing_template', {
            'company': self.company_id,
            'config': self.config_id,
            'session': self,
            'orders': orders,
            'float_repr': float_repr,
            'COUNTRY_CODE_MAP': COUNTRY_CODE_MAP,
            'total_cash': total_cash,
            'total_bank': total_bank,
            'vat_definitions': vat_definitions,
            'amounts_per_vat_id': amounts_per_vat_id_result
        })

        return ast.literal_eval(json.strip())

    def _l10n_de_send_fiskaly_cash_point_closing(self, json):
        cash_point_closing_uuid = str(uuid.uuid4())
        cash_register_resp = self.company_id._l10n_de_fiskaly_dsfinvk_rpc('GET', '/cash_registers/%s' % self.config_id.l10n_de_fiskaly_client_id)
        if cash_register_resp.status_code == 404:  # register the cash register
            self._l10n_de_create_fiskaly_cash_register()
        cash_point_closing_resp = self.company_id._l10n_de_fiskaly_dsfinvk_rpc('PUT', '/cash_point_closings/%s' % cash_point_closing_uuid, json)
        if cash_point_closing_resp.status_code != 200:
            raise UserError(_('Cash point closing error with Fiskaly: \n %s', cash_point_closing_resp.json()))
        self.write({'l10n_de_fiskaly_cash_point_closing_uuid': cash_point_closing_uuid})

    def _l10n_de_create_fiskaly_cash_register(self):
        json = {
            'cash_register_type': {
                'type': 'MASTER',
                'tss_id': self.config_id._l10n_de_get_tss_id()
            },
            'brand': 'Odoo',
            'model': 'Odoo',
            'base_currency_code': 'EUR',
            'software': {
                'version': release.version
            }
        }

        self.company_id._l10n_de_fiskaly_dsfinvk_rpc('PUT', '/cash_registers/%s' % self.config_id.l10n_de_fiskaly_client_id, json)

    def _l10n_de_fiskaly_get_vat_definitions(self):
        vat_definitions_resp = self.company_id._l10n_de_fiskaly_dsfinvk_rpc('GET', '/vat_definitions')
        vat_definitions = {}
        for vat in vat_definitions_resp.json()['data']:
            vat_definitions[vat['percentage']] = vat['vat_definition_export_id']

        return vat_definitions
