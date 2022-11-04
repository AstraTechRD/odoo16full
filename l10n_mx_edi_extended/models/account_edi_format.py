# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _l10n_mx_edi_get_invoice_cfdi_values(self, invoice):
        # OVERRIDE
        vals = super()._l10n_mx_edi_get_invoice_cfdi_values(invoice)
        customer = vals['customer']

        # Update line values for custom numbers
        for line_vals in vals['invoice_line_vals_list']:
            # Custom number
            line_vals['custom_numbers'] = line_vals['line']._l10n_mx_edi_get_custom_numbers()

        # External Trade
        if invoice.l10n_mx_edi_external_trade:
            mxn = self.env["res.currency"].search([('name', '=', 'MXN')], limit=1)
            usd = self.env["res.currency"].search([('name', '=', 'USD')], limit=1)

            if customer.country_id in self.env.ref('base.europe').country_ids:
                vals['ext_trade_num_exp'] = invoice.company_id.l10n_mx_edi_num_exporter
            else:
                vals['ext_trade_num_exp'] = None

            vals['ext_trade_rate_usd_mxn'] = usd._convert(1.0, mxn, invoice.company_id, invoice.date, round=False)

            invoice_lines_gb_products = {}
            for line_vals in vals['invoice_line_vals_list']:
                invoice_lines_gb_products.setdefault(line_vals['line'].product_id, [])
                invoice_lines_gb_products[line_vals['line'].product_id].append(line_vals)

            ext_trade_total_price_subtotal_usd = 0.0
            ext_trade_goods_details = []
            for product, line_vals_list in invoice_lines_gb_products.items():
                if len(line_vals_list) > 1:
                    weighted_prices = sum(line_vals['line'].l10n_mx_edi_price_unit_umt * line_vals['line'].l10n_mx_edi_qty_umt for line_vals in line_vals_list)
                    weights = sum(line_vals['line'].l10n_mx_edi_qty_umt for line_vals in line_vals_list) or 1
                    amount = round(weighted_prices/weights, 2)
                else:
                    amount = line_vals_list[0]['line'].l10n_mx_edi_price_unit_umt if line_vals_list else 0

                price_unit_usd = invoice.currency_id._convert(
                    amount,
                    usd,
                    invoice.company_id,
                    invoice.date,
                )

                line_total_usd = invoice.currency_id._convert(
                    sum(line_vals['price_subtotal_before_discount'] for line_vals in line_vals_list),
                    usd,
                    invoice.company_id,
                    invoice.date,
                )
                ext_trade_total_price_subtotal_usd += line_total_usd

                ext_trade_goods_details.append({
                    'product': product,
                    'quantity_aduana': sum(line_vals['line'].l10n_mx_edi_qty_umt for line_vals in line_vals_list),
                    'price_unit_usd': price_unit_usd,
                    'line_total_usd': line_total_usd,
                })

            # Override 'customer_fiscal_residence' in case of external trade.
            if customer.country_id.l10n_mx_edi_code != 'MEX':
                customer_fiscal_residence = customer.country_id.l10n_mx_edi_code
            else:
                customer_fiscal_residence = None

            vals.update({
                'ext_trade_goods_details': ext_trade_goods_details,
                'ext_trade_total_price_subtotal_usd': ext_trade_total_price_subtotal_usd,
                'ext_trade_delivery_partner': invoice.partner_shipping_id,
                'ext_trade_customer_reg_trib': customer.vat,
                'customer_fiscal_residence': customer_fiscal_residence,
            })
        return vals
