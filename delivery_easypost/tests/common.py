# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase


class EasypostTestCommon(TransactionCase):
    def setUp(self):
        super().setUp()
        self.your_company = self.env.ref("base.main_partner")
        self.your_company.write(
            {
                "name": "Odoo SA",
                "street": "44 Wall Street",
                "street2": "Suite 603",
                "city": "New York",
                "zip": 10005,
                "state_id": self.env.ref("base.state_us_27").id,
                "country_id": self.env.ref("base.us").id,
                "phone": "+1 (929) 352-6366",
            }
        )

        self.jackson = self.env.ref("base.res_partner_10")
        self.jackson.write(
            {
                "street": "1515 Main Street",
                "street2": "",
                "city": "Columbia",
                "zip": 29201,
                "state_id": self.env.ref("base.state_us_41").id,
                "country_id": self.env.ref("base.us").id,
            }
        )
        self.agrolait = self.env.ref("base.res_partner_2")
        self.agrolait.write(
            {
                "country_id": self.env.ref("base.be").id,
                "city": "Auderghem-Ouderghem",
                "street": "Avenue Edmond Van Nieuwenhuyse",
                "zip": "1160",
            }
        )
        # configure rounding, so that we can enter an extra-light product
        conf = self.env["ir.config_parameter"]
        conf.set_param("product.weight_in_lbs", "1")
        precision = self.env.ref("product.decimal_stock_weight")
        precision.digits = 4
        self.uom_lbs = self.env.ref("uom.product_uom_lb")
        self.uom_lbs.rounding = 0.0001
        self.server = self.env["product.product"].create(
            {
                "name": "server",
                "type": "consu",
                "weight": 3.0,
                "volume": 4.0,
            }
        )
        self.miniServer = self.env["product.product"].create(
            {
                "name": "mini server",
                "type": "consu",
                "weight": 2.0,
                "volume": 0.35,
            }
        )
        self.microServer = self.env["product.product"].create(
            {
                "name": "micro server",
                "type": "consu",
                "weight": 0.0025,
                "volume": 0.35,
            }
        )

        self.easypost_fedex_carrier_product = self.env["product.product"].create(
            {
                "name": "Fedex Easypost",
                "type": "service",
            }
        )

        self.easypost_fedex_carrier = self.env["delivery.carrier"].create(
            {
                "name": "EASYPOST FedEx",
                "delivery_type": "easypost",
                "easypost_test_api_key": "EZTKc116818834b24215a47fafc556e46340LYwlOtD5xn1m1euw0HmZ5A",
                "easypost_production_api_key": "zhiDnLnzKCVkelNzVAfWEQ",
                "product_id": self.easypost_fedex_carrier_product.id,
            }
        )
        product_type_wizard = self.easypost_fedex_carrier.action_get_carrier_type()
        self.easypost_fedex_carrier.easypost_delivery_type = "FedEx"
        self.easypost_fedex_carrier.easypost_delivery_type_id = product_type_wizard["context"]["carrier_types"]["FedEx"]

        self.fedex_default_package_type = self.env["stock.package.type"].create(
            {
                "name": "My FedEx Box",
                "package_carrier_type": "easypost",
                "max_weight": 10,
                "height": 10,
                "packaging_length": 10,
                "width": 10,
            }
        )
        self.easypost_fedex_carrier.easypost_default_package_type_id = self.fedex_default_package_type
