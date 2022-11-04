# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io

from lxml import etree, objectify
from os.path import join
from werkzeug.urls import url_quote

from odoo import api, models, tools


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    XSD_COMPLEMENTS = [
        ['http://www.sat.gob.mx/servicioparcialconstruccion',
         'http://www.sat.gob.mx/sitio_internet/cfd/servicioparcialconstruccion/servicioparcialconstruccion.xsd'],
        ['http://www.sat.gob.mx/EstadoDeCuentaCombustible',
         'http://www.sat.gob.mx/sitio_internet/cfd/EstadoDeCuentaCombustible/ecc12.xsd'],
        ['http://www.sat.gob.mx/donat',
         'http://www.sat.gob.mx/sitio_internet/cfd/donat/donat11.xsd'],
        ['http://www.sat.gob.mx/divisas',
         'http://www.sat.gob.mx/sitio_internet/cfd/divisas/Divisas.xsd'],
        ['http://www.sat.gob.mx/implocal',
         'http://www.sat.gob.mx/sitio_internet/cfd/implocal/implocal.xsd'],
        ['http://www.sat.gob.mx/leyendasFiscales',
         'http://www.sat.gob.mx/sitio_internet/cfd/leyendasFiscales/leyendasFisc.xsd'],
        ['http://www.sat.gob.mx/pfic',
         'http://www.sat.gob.mx/sitio_internet/cfd/pfic/pfic.xsd'],
        ['http://www.sat.gob.mx/TuristaPasajeroExtranjero',
         'http://www.sat.gob.mx/sitio_internet/cfd/TuristaPasajeroExtranjero/TuristaPasajeroExtranjero.xsd'],
        ['http://www.sat.gob.mx/detallista',
         'http://www.sat.gob.mx/sitio_internet/cfd/detallista/detallista.xsd'],
        ['http://www.sat.gob.mx/registrofiscal',
         'http://www.sat.gob.mx/sitio_internet/cfd/cfdiregistrofiscal/cfdiregistrofiscal.xsd'],
        ['http://www.sat.gob.mx/nomina12',
         'http://www.sat.gob.mx/sitio_internet/cfd/nomina/nomina12.xsd'],
        ['http://www.sat.gob.mx/pagoenespecie',
         'http://www.sat.gob.mx/sitio_internet/cfd/pagoenespecie/pagoenespecie.xsd'],
        ['http://www.sat.gob.mx/valesdedespensa',
         'http://www.sat.gob.mx/sitio_internet/cfd/valesdedespensa/valesdedespensa.xsd'],
        ['http://www.sat.gob.mx/consumodecombustibles',
         'http://www.sat.gob.mx/sitio_internet/cfd/consumodecombustibles/consumodecombustibles.xsd'],
        ['http://www.sat.gob.mx/aerolineas',
         'http://www.sat.gob.mx/sitio_internet/cfd/aerolineas/aerolineas.xsd'],
        ['http://www.sat.gob.mx/notariospublicos',
         'http://www.sat.gob.mx/sitio_internet/cfd/notariospublicos/notariospublicos.xsd'],
        ['http://www.sat.gob.mx/vehiculousado',
         'http://www.sat.gob.mx/sitio_internet/cfd/vehiculousado/vehiculousado.xsd'],
        ['http://www.sat.gob.mx/renovacionysustitucionvehiculos',
         'http://www.sat.gob.mx/sitio_internet/cfd/renovacionysustitucionvehiculos/renovacionysustitucionvehiculos.xsd'],
        ['http://www.sat.gob.mx/certificadodestruccion',
         'http://www.sat.gob.mx/sitio_internet/cfd/certificadodestruccion/certificadodedestruccion.xsd'],
        ['http://www.sat.gob.mx/arteantiguedades',
         'http://www.sat.gob.mx/sitio_internet/cfd/arteantiguedades/obrasarteantiguedades.xsd'],
        ['http://www.sat.gob.mx/ComercioExterior11',
         'http://www.sat.gob.mx/sitio_internet/cfd/ComercioExterior11/ComercioExterior11.xsd'],
        ['http://www.sat.gob.mx/Pagos',
         'http://www.sat.gob.mx/sitio_internet/cfd/Pagos/Pagos10.xsd'],
        ['http://www.sat.gob.mx/iedu',
         'http://www.sat.gob.mx/sitio_internet/cfd/iedu/iedu.xsd'],
        ['http://www.sat.gob.mx/ventavehiculos',
         'http://www.sat.gob.mx/sitio_internet/cfd/ventavehiculos/ventavehiculos11.xsd'],
        ['http://www.sat.gob.mx/terceros',
         'http://www.sat.gob.mx/sitio_internet/cfd/terceros/terceros11.xsd'],
        ['http://www.sat.gob.mx/spei',
         'http://www.sat.gob.mx/sitio_internet/cfd/spei/spei.xsd'],
        ['http://www.sat.gob.mx/acreditamiento',
         'http://www.sat.gob.mx/sitio_internet/cfd/acreditamiento/AcreditamientoIEPS10.xsd'],
        ['http://www.sat.gob.mx/TimbreFiscalDigital',
         'http://www.sat.gob.mx/sitio_internet/cfd/TimbreFiscalDigital/TimbreFiscalDigitalv11.xsd'],
    ]

    @api.model
    def _l10n_mx_edi_load_xsd_files_recursion(self, url, force_reload):
        xsd_name = url.split('/')[-1].replace('.', '_')
        xsd_name = f'xsd_cached_{xsd_name}'
        modify_xsd_content = None
        if xsd_name == 'xsd_cached_cfdv33_xsd':
            modify_xsd_content = self._load_xsd_complements
        attachment = tools.load_xsd_files_from_url(self.env, url, xsd_name, force_reload=force_reload, modify_xsd_content=modify_xsd_content)

        raw_object = objectify.fromstring(attachment.raw)
        sub_urls = raw_object.xpath('//xs:import', namespaces={'xs': 'http://www.w3.org/2001/XMLSchema'})
        for s_url in sub_urls:
            s_url_catch = self._l10n_mx_edi_load_xsd_files_recursion(s_url.get('schemaLocation'), force_reload)
            s_url.attrib['schemaLocation'] = url_quote(s_url_catch)

        file_store = tools.config.filestore(self.env.cr.dbname)
        return join(file_store, attachment.store_fname)

    @api.model
    def _l10n_mx_edi_load_xsd_files(self, force_reload=False):
        self._l10n_mx_edi_load_xsd_files_recursion('http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd', force_reload)
        self._l10n_mx_edi_load_xsd_files_recursion('http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd', force_reload)
        return

    @api.model
    def l10n_mx_edi_validate_xml_from_attachment(self, xml_content, xsd_name):
        attachment = self.sudo().env.ref(f'l10n_mx_edi.{xsd_name}', False)
        if not attachment:
            return
        with io.BytesIO(attachment.raw) as xsd:
            return tools.xml_utils._check_with_xsd(xml_content, xsd)

    @api.model
    def _load_xsd_complements(self, content):
        content_object = objectify.fromstring(content)
        for complement in self.XSD_COMPLEMENTS:
            xsd = {'namespace': complement[0], 'schemaLocation': complement[1]}
            node = etree.Element('{http://www.w3.org/2001/XMLSchema}import', xsd)
            content_object.insert(0, node)
        return etree.tostring(content_object, pretty_print=True)
