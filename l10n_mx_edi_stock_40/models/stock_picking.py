# -*- coding: utf-8 -*-

from lxml import etree, objectify

from odoo import models

class Picking(models.Model):
    _inherit = 'stock.picking'

    def _l10n_mx_edi_get_cadena_xslt(self):
        return 'l10n_mx_edi_40/data/4.0/cadenaoriginal_4_0.xslt'

    def _l10n_mx_edi_dg_render(self, values):
        return self.env['ir.qweb']._render('l10n_mx_edi_stock_40.cfdi_cartaporte_40', values)

    def _l10n_mx_edi_validate_with_xsd(self, xml_str, raise_error=False):
        ''' OVERRIDE l10n_mx_edi_stock
        '''
        combined_xsd_str = '''
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
            <xs:import namespace="http://www.sat.gob.mx/cfd/4" schemaLocation="http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd"/>
            <xs:import namespace="http://www.sat.gob.mx/CartaPorte20" schemaLocation="http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte/CartaPorte20.xsd"/>
        </xs:schema>
        '''
        xmlschema = etree.XMLSchema(objectify.fromstring(combined_xsd_str))
        xml_doc = objectify.fromstring(xml_str)
        result = xmlschema.validate(xml_doc)
        if not result and raise_error:
            xmlschema.assertValid(xml_doc)  #if the document is invalid, raise the error for debugging
        return result
