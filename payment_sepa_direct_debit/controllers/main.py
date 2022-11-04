# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import _, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.addons.base_iban.models.res_partner_bank import validate_iban
from odoo.addons.iap.tools import iap_tools
from odoo.addons.payment_sepa_direct_debit.models.sdd_mandate import INT_PHONE_NUMBER_FORMAT_REGEX
from odoo.addons.phone_validation.tools.phone_validation import phone_sanitize_numbers

_logger = logging.getLogger(__name__)


class SepaDirectDebitController(http.Controller):

    @http.route('/payment/sepa_direct_debit/form_configuration', type='json', auth='public')
    def sdd_form_configuration(self, provider_id, partner_id):
        """ Get the configuration for the SEPA Direct Debit form.

        :param int provider_id: The provider handling the transaction, as a `payment.provider` id
        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :return: The configuration of the form
        :rtype: dict
        """
        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id).exists()
        partner_sudo = request.env['res.partner'].sudo().browse(partner_id).exists()
        logged_in = not request.env.user._is_public() \
                    and partner_id == request.env.user.partner_id.id
        return {
            'partner_name': logged_in and partner_sudo.name,
            'partner_email': logged_in and partner_sudo.email,
            'signature_required': provider_sudo.sdd_signature_required,
            'sms_verification_required': provider_sudo.sdd_sms_verification_required,
        }

    @http.route('/payment/sepa_direct_debit/get_mandate', type='json', auth='public')
    def sdd_get_mandate(self, provider_id, partner_id, iban, phone):
        """ Return the SDD mandate linked to the partner and iban.

        The phone is only used to create a new mandate if it was not found.

        :param int provider_id: The provider handling the transaction, as a `payment.provider` id
        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :param str iban: The IBAN number of the partner's bank account
        :param str phone: The phone number used to verify the mandate
        :return: The mandate id
        :rtype: int
        """
        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id).exists()
        iban = self._sdd_validate_and_format_iban(iban)
        phone = self._sdd_validate_and_format_phone(phone)
        mandate = provider_sudo._sdd_find_or_create_mandate(partner_id, iban, phone)
        return mandate.id

    @http.route('/payment/sepa_direct_debit/send_verification_sms', type='json', auth='public')
    def sdd_send_verification_sms(self, provider_id, mandate_id, phone):
        """ Send a verification code from the mandate to the given phone.

        :param int provider_id: The provider handling the transaction, as a `payment.provider` id
        :param int mandate_id: The mandate whose phone number to verify, as an `sdd.mandate` id
        :param str phone: The phone number of the partner
        :return: None
        :raise: UserError if SMS verification is disabled on the provider
        :raise: UserError in case of insufficient IAP credits
        :raise: ValidationError if the mandate ID is incorrect
        """
        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id).exists()
        if not provider_sudo.sdd_sms_verification_required:
            raise UserError("SEPA: " + _("SMS verification is disabled."))

        mandate_sudo = request.env['sdd.mandate'].sudo().browse(mandate_id).exists()
        if not mandate_sudo:
            raise ValidationError("SEPA: " + _("Unknown mandate ID."))

        phone = self._sdd_validate_and_format_phone(phone)
        try:
            mandate_sudo._send_verification_code(phone)
        except iap_tools.InsufficientCreditError:
            raise UserError("SEPA: " + _("SMS could not be sent due to insufficient credit."))

    @http.route('/payment/sepa_direct_debit/create_token', type='json', auth='public')
    def sdd_create_token(
        self, provider_id, partner_id, iban, mandate_id=None, phone=None, verification_code=None,
        signer=None, signature=None
    ):
        """ Create a token linked to the mandate and return it.

        If the mandate is not provided (i.e. if it was not previously used to send the SMS code), it
        is fetched or created based on the partner and IBAN.

        :param int provider_id: The provider handling the transaction, as a `payment.provider` id
        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :param str iban: The IBAN number of the partner's bank account
        :param int mandate_id: The mandate to link to the token, as an `sdd.mandate` id
        :param str phone: The phone number of the partner
        :param str verification_code: The verification code sent to the given phone number
        :param str signer: The name provided with the signature
        :param bytes signature: The signature drawn in the form
        :return: The token id
        :rtype: int
        :raise: ValidationError if a configuration-specific required parameter is not provided
        :raise: ValidationError if the mandate ID is incorrect
        """
        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id).exists()

        # Verify that all configuration-specific required parameters are provided.
        iban = self._sdd_validate_and_format_iban(iban)
        if provider_sudo.sdd_sms_verification_required:
            if not phone or not verification_code:
                raise ValidationError("SEPA: " + _("The phone number must be provided and verified."))
            else:
                phone = self._sdd_validate_and_format_phone(phone)
        if provider_sudo.sdd_signature_required and (not signer or not signature):
            raise ValidationError("SEPA: " + _("The name and signature must be provided."))

        # Get the mandate from its id if provided, from the IBAN otherwise
        if mandate_id:
            mandate_sudo = request.env['sdd.mandate'].sudo().browse(mandate_id).exists()
            if not mandate_sudo:
                raise ValidationError("SEPA: " + _("Unknown mandate ID."))
        else:
            mandate_sudo = provider_sudo._sdd_find_or_create_mandate(partner_id, iban, phone)

        # Create the token and return its id
        token_sudo = provider_sudo._sdd_create_token_for_mandate(
            partner_id, iban, mandate_sudo, phone=phone, verification_code=verification_code,
            signer=signer, signature=signature
        )
        return token_sudo.id

    def _sdd_validate_and_format_iban(self, iban):
        """ Validate the provided IBAN and return its formatted value.

        :param str iban: The IBAN to validate and format
        :return: The formatted IBAN
        :rtype: str
        :raise: ValidationError if the IBAN is invalid
        """
        iban = sanitize_account_number(iban)
        validate_iban(iban)
        if not iban:
            raise ValidationError("SEPA: " + _("Missing or invalid IBAN."))
        return iban

    def _sdd_validate_and_format_phone(self, phone):
        """ Validate the provided phone number and return its formatted value.

        :param str phone: The phone number to validate and format
        :return: The formatted phone number
        :rtype: str
        :raise: ValidationError if the phone number is invalid
        """
        if not re.match(INT_PHONE_NUMBER_FORMAT_REGEX, phone):
            raise ValidationError(
                "SEPA: " + _("The phone number should be in international format.")
            )
        phone = phone_sanitize_numbers([phone], None, None).get(phone, {}).get('sanitized')
        if not phone:
            raise ValidationError("SEPA: " + _("Incorrect phone number."))
        return phone
