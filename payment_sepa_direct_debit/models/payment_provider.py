# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('sepa_direct_debit', "SEPA Direct Debit")],
        ondelete={'sepa_direct_debit': 'set default'})
    sdd_signature_required = fields.Boolean(
        string="Online Signature", help="Whether a signature is required to create a new mandate.")
    sdd_sms_verification_required = fields.Boolean(
        string="Phone Verification", help="Whether phone numbers must be verified by an SMS code.")
    sdd_sms_credits = fields.Monetary(
        string="SMS Credits", currency_field='main_currency_id', compute='_compute_sdd_sms_credits'
    )

    #=== COMPUTE METHODS ===#

    @api.depends('code')
    def _compute_view_configuration_fields(self):
        """ Override of payment to hide the credentials page.

        :return: None
        """
        super()._compute_view_configuration_fields()
        self.filtered(lambda p: p.code == 'sepa_direct_debit').update({
            'show_credentials_page': False,
            'show_allow_tokenization': False,
            'show_payment_icon_ids': False,
            'show_done_msg': False,
            'show_cancel_msg': False,
        })

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'sepa_direct_debit').update({
            'support_tokenization': True,
        })

    @api.depends('code')
    def _compute_sdd_sms_credits(self):
        sms_credits = self.env['iap.account'].get_credits('sms')
        self.filtered(lambda p: p.code == 'sepa_direct_debit').sdd_sms_credits = sms_credits
        self.filtered(lambda p: p.code != 'sepa_direct_debit').sdd_sms_credits = 0

    #=== CONSTRAINT METHODS ===#

    @api.constrains('state', 'journal_id')
    def _check_journal_iban_is_valid(self):
        """ Check that the bank account of the payment journal is a valid IBAN. """
        for provider in self.filtered(
            lambda p: p.code == 'sepa_direct_debit' and p.state == 'enabled'
        ):
            if provider.journal_id.bank_account_id.acc_type != 'iban':
                raise ValidationError(_("The bank account of the journal is not a valid IBAN."))

    @api.constrains('state', 'company_id')
    def _check_has_creditor_identifier(self):
        """ Check that the company has a creditor identifier. """
        for provider in self.filtered(
            lambda p: p.code == 'sepa_direct_debit' and p.state == 'enabled'
        ):
            if not provider.company_id.sdd_creditor_identifier:
                raise ValidationError(_(
                    "Your company must have a creditor identifier in order to issue a SEPA Direct "
                    "Debit payment request. It can be set in Accounting settings."
                ))

    @api.constrains('available_country_ids')
    def _check_country_in_sepa_zone(self):
        """ Check that all selected countries are in the SEPA zone. """
        sepa_countries = self.env.ref('base.sepa_zone').country_ids
        for provider in self.filtered(lambda p: p.code == 'sepa_direct_debit'):
            non_sepa_countries = provider.available_country_ids - sepa_countries
            if non_sepa_countries:
                raise ValidationError(_(
                    "Restricted to countries in the SEPA zone. Forbidden countries: %s",
                    ', '.join(non_sepa_countries.mapped('name'))
                ))

    #=== ACTION METHODS ===#

    def action_buy_sms_credits(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.env['iap.account'].get_credits_url(base_url='', service_name='sms'),
        }

    #=== BUSINESS METHODS ===#

    def _is_tokenization_required(self, **kwargs):
        """ Override of payment to hide the "Save my payment details" input in checkout forms.

        :return: Whether the provider is SEPA
        :rtype: bool
        """
        res = super()._is_tokenization_required(**kwargs)
        if len(self) != 1 or self.code != 'sepa_direct_debit':
            return res

        return True

    def _sdd_find_or_create_mandate(self, partner_id, iban, phone=None):
        """ Find or create the SDD mandate verified by the given phone.

        Note: self.ensure_one()

        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :param str iban: The sanitized IBAN number of the partner's bank account
        :param str phone: The sanitized phone number used to verify the mandate
        :return: The SDD mandate
        :rtype: recordset of `sdd.mandate`
        """
        self.ensure_one()

        commercial_partner_id = self.env['res.partner'].browse(partner_id).commercial_partner_id.id
        partner_bank = self._sdd_find_or_create_partner_bank(partner_id, iban)
        mandate = self.env['sdd.mandate'].search([
            ('state', 'not in', ['closed', 'revoked']),
            ('start_date', '<=', datetime.now()),
            '|', ('end_date', '>=', datetime.now()), ('end_date', '=', None),
            ('partner_id', '=', commercial_partner_id),
            ('partner_bank_id', '=', partner_bank.id),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not mandate:
            mandate = self.env['sdd.mandate'].create({
                'partner_id': commercial_partner_id,
                'partner_bank_id': partner_bank.id,
                'start_date': datetime.now(),
                'payment_journal_id': self.journal_id.id,
                'state': 'draft',
                'phone_number': phone,
            })
        return mandate

    def _sdd_find_or_create_partner_bank(self, partner_id, iban):
        """ Find or create the partner bank with the given iban.

        Note: self.ensure_one()

        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :param str iban: The sanitized IBAN number of the partner's bank account
        :return: The partner bank
        :rtype: recordset of `res.partner.bank`
        """
        self.ensure_one()

        ResPartnerBank = self.env['res.partner.bank']
        commercial_partner_id = self.env['res.partner'].browse(partner_id).commercial_partner_id.id
        partner_bank = ResPartnerBank.search([
            ('sanitized_acc_number', '=', iban),
            ('partner_id', 'child_of', commercial_partner_id),
        ])
        if not partner_bank:
            partner_bank = ResPartnerBank.create({
                'acc_number': iban,
                'partner_id': partner_id,
                'company_id': self.company_id.id,
            })
        return partner_bank

    def _sdd_create_token_for_mandate(
        self, partner_id, iban, mandate, phone=None, verification_code=None, signer=None,
        signature=None
    ):
        """ Create a token linked to the mandate with the obfuscated IBAN as name and return it.

        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :param str iban: The sanitized IBAN number of the partner's bank account
        :param recordset mandate: The mandate to link to the token, as an `sdd.mandate` record
        :param str phone: The phone number of the partner
        :param str verification_code: The verification code sent to the given phone number
        :param str signer: The name provided with the signature
        :param bytes signature: The signature drawn in the form
        :return: The token
        :rtype: recordset of `payment.token`
        :raise: AccessError if the partner is different than that of the mandate
        """
        partner = self.env['res.partner'].browse(partner_id).exists()

        # Since we're in a sudoed env, we need to verify the partner
        if mandate.partner_id != partner.commercial_partner_id:
            raise AccessError("SEPA: " + _("The mandate owner and customer do not match."))

        token = self.env['payment.token'].create({
            'provider_id': self.id,
            'payment_details': iban,
            'partner_id': partner_id,
            'provider_ref': mandate.name,
            'verified': True,
            'sdd_mandate_id': mandate.id,
        })
        mandate._update_mandate(
            phone=phone, code=verification_code, signer=signer, signature=signature
        )
        return token
