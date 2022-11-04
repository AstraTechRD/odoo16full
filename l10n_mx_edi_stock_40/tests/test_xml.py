# -*- coding: utf-8 -*-

from .common import TestMXDeliveryGuideCommon

from odoo.tests import tagged

@tagged('post_install', 'post_install_l10n', '-at_install')
class TestGenerateMXDeliveryGuide(TestMXDeliveryGuideCommon):
    def test_generate_delivery_guide(self):
        cfdi = self.picking._l10n_mx_edi_create_delivery_guide()
        expected_cfdi = '''
            <cfdi:Comprobante
              xmlns:cartaporte20="http://www.sat.gob.mx/CartaPorte20"
              xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
              xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
              Certificado="___ignore___"
              NoCertificado="___ignore___"
              Sello="___ignore___"
              Moneda="XXX"
              Serie="NWHOUT"
              SubTotal="0"
              TipoDeComprobante="T"
              Total="0"
              Version="4.0"
              xsi:schemaLocation="http://www.sat.gob.mx/cfd/4 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv40.xsd http://www.sat.gob.mx/CartaPorte20 http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte/CartaPorte20.xsd http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte20/CartaPorte20.xsd"
              Fecha="___ignore___"
              Folio="00001"
              Exportacion="01"
              LugarExpedicion="20928">
              <cfdi:Emisor Nombre="ESCUELA KEMPER URGATE" RegimenFiscal="601" Rfc="EKU9003173C9"/>
              <cfdi:Receptor UsoCFDI="S01" Nombre="ESCUELA KEMPER URGATE" Rfc="EKU9003173C9" RegimenFiscalReceptor="601" DomicilioFiscalReceptor="20928"/>
              <cfdi:Conceptos>
                <cfdi:Concepto Importe="0.00" ValorUnitario="0.00" NoIdentificacion="01" Cantidad="10.000000" ClaveProdServ="56101500" ClaveUnidad="H87" Descripcion="Product A" Unidad="Units" ObjetoImp="01"/>
              </cfdi:Conceptos>
              <cfdi:Complemento>
                <cartaporte20:CartaPorte Version="2.0" TranspInternac="No" TotalDistRec="120">
                  <cartaporte20:Ubicaciones>
                    <cartaporte20:Ubicacion TipoUbicacion="Origen" IDUbicacion="___ignore___" FechaHoraSalidaLlegada="___ignore___" RFCRemitenteDestinatario="EKU9003173C9">
                      <cartaporte20:Domicilio Calle="Campobasso Norte 3206 - 9000" CodigoPostal="20928" Estado="AGU" Pais="MEX"/>
                    </cartaporte20:Ubicacion>
                    <cartaporte20:Ubicacion TipoUbicacion="Destino" IDUbicacion="___ignore___" DistanciaRecorrida="120" FechaHoraSalidaLlegada="___ignore___" RFCRemitenteDestinatario="ICV060329BY0">
                      <cartaporte20:Domicilio Calle="Street Calle" CodigoPostal="33826" Estado="CHH" Pais="MEX"/>
                    </cartaporte20:Ubicacion>
                  </cartaporte20:Ubicaciones>
                  <cartaporte20:Mercancias NumTotalMercancias="1" PesoBrutoTotal="10.000" UnidadPeso="KGM">
                    <cartaporte20:Mercancia BienesTransp="56101500" Cantidad="10.000000" ClaveUnidad="H87" Descripcion="Product A" PesoEnKg="10.000">
                      <cartaporte20:CantidadTransporta Cantidad="10.000000" IDOrigen="___ignore___" IDDestino="___ignore___"/>
                    </cartaporte20:Mercancia>
                    <cartaporte20:Autotransporte NumPermisoSCT="DEMOPERMIT" PermSCT="TPAF10">
                      <cartaporte20:IdentificacionVehicular AnioModeloVM="2020" ConfigVehicular="T3S1" PlacaVM="ABC123"/>
                      <cartaporte20:Seguros AseguraRespCivil="DEMO INSURER" PolizaRespCivil="DEMO POLICY"/>
                      <cartaporte20:Remolques>
                        <cartaporte20:Remolque SubTipoRem="CTR003" Placa="trail1"/>
                      </cartaporte20:Remolques>
                    </cartaporte20:Autotransporte>
                  </cartaporte20:Mercancias>
                  <cartaporte20:FiguraTransporte>
                    <cartaporte20:TiposFigura TipoFigura="01" RFCFigura="VAAM130719H60" NumLicencia="a234567890">
                    </cartaporte20:TiposFigura>
                    <cartaporte20:TiposFigura TipoFigura="02" RFCFigura="EKU9003173C9">
                      <cartaporte20:PartesTransporte ParteTransporte="PT05"/>
                    </cartaporte20:TiposFigura>
                  </cartaporte20:FiguraTransporte>
                </cartaporte20:CartaPorte>
              </cfdi:Complemento>
            </cfdi:Comprobante>
        '''
        current_etree = self.get_xml_tree_from_string(cfdi)
        expected_etree = self.get_xml_tree_from_string(expected_cfdi)
        self.assertXmlTreeEqual(current_etree, expected_etree)
