# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_pe_withhold_code = fields.Selection(
        selection=[
            ('001', 'Azúcar'),
            ('003', 'Alcohol etílico'),
            ('004', 'Recursos hidrobiológicos'),
            ('005', 'Maíz amarillo duro'),
            ('006', 'Algodón'),
            ('007', 'Caña de azúcar'),
            ('008', 'Madera'),
            ('009', 'Arena y piedra'),
            ('010', 'Residuos, subproductos, desechos, recortes y desperdicios'),
            ('011', 'Bienes del inciso A) del Apéndice I de la Ley del IGV'),
            ('012', 'Intermediación laboral y tercerización'),
            ('013', 'Animales vivos'),
            ('014', 'Carnes y despojos comestibles'),
            ('015', 'Abonos, cueros y pieles de origen animal'),
            ('016', 'Aceite de pescado'),
            ('017', 'Harina, polvo y “pellets” de pescado, crustáceos, moluscos y demás invertebrados acuáticos'),
            ('018', 'Embarcaciones pesqueras'),
            ('019', 'Arrendamiento de bienes muebles'),
            ('020', 'Mantenimiento y reparación de bienes muebles'),
            ('021', 'Movimiento de carga'),
            ('022', 'Otros servicios empresariales'),
            ('023', 'Leche'),
            ('024', 'Comisión mercantil'),
            ('025', 'Fabricación de bienes por encargo'),
            ('026', 'Servicio de transporte de personas'),
            ('029', 'Algodón en rama sin desmontar'),
            ('030', 'Contratos de construcción'),
            ('031', 'Oro gravado con el IGV'),
            ('032', 'Páprika y otros frutos de los géneros capsicum o pimienta'),
            ('033', 'Espárragos'),
            ('034', 'Minerales metálicos no auríferos'),
            ('035', 'Bienes exonerados del IGV'),
            ('036', 'Oro y demás minerales metálicos exonerados del IGV'),
            ('037', 'Demás servicios gravados con el IGV'),
            ('039', 'Minerales no metálicos'),
            ('040', 'Bien inmueble gravado con IGV')
        ],
        string="Withhold code",
        help="Catalog No. 54 SUNAT, used functionally to document in the printed document on invoices that need to "
             "have the proper SPOT text")
    l10n_pe_withhold_percentage = fields.Float(
        string="Withhold Percentage",
        help="Percentages of detraction informed in the Annexed I Resolution 183-2004/SUNAT, it depends on the "
             "Withhold code but you need to read the resolution")
