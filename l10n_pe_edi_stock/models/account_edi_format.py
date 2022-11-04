from zeep.wsse.username import UsernameToken
from odoo import api, models, _lt


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _l10n_pe_edi_sign_service_sunat(self, company, edi_filename, edi_str, latam_document_type, serie=False):
        """This entire override is just because SUNAT has a different place to put the Delivery Guide than Digiflow
        and it is done like that because we would need to pass a different WSDL in the credentials to Delivery Guide.
        """
        if latam_document_type != '09':
            return super()._l10n_pe_edi_sign_service_sunat(company, edi_filename, edi_str, latam_document_type,
                                                           serie=serie)
        credentials = self._l10n_pe_edi_get_sunat_credentials_guide(company)
        return self._l10n_pe_edi_sign_service_sunat_digiflow_common(
            company, edi_filename, edi_str, credentials, latam_document_type)

    def _l10n_pe_edi_get_sunat_credentials_guide(self, company):
        self.ensure_one()
        res = {'fault_ns': 'soap-env'}
        if company.l10n_pe_edi_test_env:
            res.update({
                'wsdl': 'https://e-beta.sunat.gob.pe/ol-ti-itemision-guia-gem-beta/billService?wsdl',
                'token': UsernameToken('MODDATOS', 'MODDATOS'),
            })
        else:
            res.update({
                'wsdl': 'https://e-guiaremision.sunat.gob.pe/ol-ti-itemision-guia-gem/billService?wsdl',
                'token': UsernameToken(company.l10n_pe_edi_provider_username, company.l10n_pe_edi_provider_password),
            })
        return res

    @api.model
    def _l10n_pe_edi_get_cdr_error_messages(self):
        """Extend codes for delivery guide"""
        result = super()._l10n_pe_edi_get_cdr_error_messages()
        result.update({
            '1068': _lt("You need to configure the identification number on the transport operator."),
        })
        return result
