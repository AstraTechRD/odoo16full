from odoo import models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def _get_edi_attachments(self, document):
        if not document.attachment_id or document.edi_format_id.code != 'pe_ubl_2_1':
            return super()._get_edi_attachments(document)
        return {'attachments': document.edi_format_id._l10n_pe_edi_unzip_all_edi_documents(document.attachment_id.datas)}
