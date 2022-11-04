# -*- coding: utf-8 -*-
import logging
import re
import time

from odoo import models, _

_logger = logging.getLogger(__name__)

TOLERANCE = 0.02  # tolerance applied to the total when searching for a matching purchase order


class AccountMove(models.Model):
    _inherit = ['account.move']

    def get_user_infos(self):
        def transform_numbers_to_regex(string):
            r"""Transforms each number of a string to their regex equivalent, i.e. P00042-12 -> P\d{5}-\d{2}"""
            digits_count = 0
            new_string = ''
            for c in string:
                if c.isdigit():
                    digits_count += 1
                else:
                    if digits_count:
                        new_string += r'\d{{{}}}'.format(digits_count) if digits_count > 1 else r'\d'
                    digits_count = 0
                    new_string += c
            if digits_count:
                new_string += r'\d{{{}}}'.format(digits_count) if digits_count > 1 else r'\d'
            return new_string

        user_infos = super(AccountMove, self).get_user_infos()
        po_sequence = self.env['ir.sequence'].search([('code', '=', 'purchase.order'), ('company_id', 'in', [self.company_id.id, False])], order='company_id', limit=1)
        if po_sequence:
            po_regex_prefix, po_regex_suffix = po_sequence._get_prefix_suffix()
            po_regex_prefix = transform_numbers_to_regex(re.escape(po_regex_prefix))
            po_regex_suffix = transform_numbers_to_regex(re.escape(po_regex_suffix))
            po_regex_sequence = r'\d{{{}}}'.format(po_sequence.padding)
            user_infos['purchase_order_regex'] = '^' + po_regex_prefix + po_regex_sequence + po_regex_suffix + '$'
        return user_infos

    def find_matching_subset_invoice_lines(self, invoice_lines, goal_total, timeout=10):
        """ The problem of finding the subset of `invoice_lines` which sums up to `goal_total` reduces to the 0-1 Knapsack problem.
        The dynamic programming approach to solve this problem is most of the time slower than this because identical sub-problems don't arise often enough.
        It returns the list of invoice lines which sums up to `goal_total` or an empty list if multiple or no solutions were found."""
        def _find_matching_subset_invoice_lines(lines, goal):
            if time.time() - start_time > timeout:
                raise TimeoutError
            solutions = []
            for i, line in enumerate(lines):
                if line['amount_to_invoice'] < goal - TOLERANCE:
                    sub_solutions = _find_matching_subset_invoice_lines(lines[i + 1:], goal - line['amount_to_invoice'])
                    solutions.extend((line, *solution) for solution in sub_solutions)
                elif goal - TOLERANCE <= line['amount_to_invoice'] <= goal + TOLERANCE:
                    solutions.append([line])
                if len(solutions) > 1:
                    # More than 1 solution found, we can't know for sure which is the correct one, so we don't return any solution
                    return []
            return solutions
        start_time = time.time()
        try:
            subsets = _find_matching_subset_invoice_lines(sorted(invoice_lines, key=lambda line: line['amount_to_invoice'], reverse=True), goal_total)
            return subsets[0] if subsets else []
        except TimeoutError:
            _logger.warning("Timed out during search of a matching subset of invoice lines")
            return []

    def _set_purchase_orders(self, purchase_orders):
        with self.env.cr.savepoint():
            with self._get_edi_creation() as move_form:
                for purchase_order in purchase_orders:
                    move_form.purchase_id = purchase_order
                    move_form._onchange_purchase_auto_complete()

    def _save_form(self, ocr_results, force_write=False):
        if self.move_type == 'in_invoice':
            common_domain = [('company_id', '=', self.company_id.id), ('state', '=', 'purchase'), ('invoice_status', 'in', ('to invoice', 'no'))]
            purchase_orders_ocr = ocr_results['purchase_order']['selected_values'] if 'purchase_order' in ocr_results else []
            total_ocr = ocr_results['total']['selected_value']['content'] if 'total' in ocr_results else 0.0

            matching_pos = self.env['purchase.order']
            if purchase_orders_ocr:
                purchase_orders_found = [po['content'] for po in purchase_orders_ocr]
                matching_pos |= self.env['purchase.order'].search(common_domain + [('name', 'in', purchase_orders_found)])

                if not matching_pos:
                    matching_po = self.env['purchase.order'].search(common_domain + [('partner_ref', 'in', purchase_orders_found)])
                    matching_pos |= matching_po

            if not matching_pos:
                supplier_ocr = ocr_results['supplier']['selected_value']['content'] if 'supplier' in ocr_results else ""
                vat_number_ocr = ocr_results['VAT_Number']['selected_value']['content'] if 'VAT_Number' in ocr_results else ""

                partner_id = self.find_partner_id_with_vat(vat_number_ocr)
                if partner_id:
                    partner_id = partner_id.id
                else:
                    partner_id = self.find_partner_id_with_name(supplier_ocr)
                if partner_id and total_ocr:
                    purchase_id_domain = common_domain + [('partner_id', 'child_of', [partner_id]), ('amount_total', '>=', total_ocr - TOLERANCE), ('amount_total', '<=', total_ocr + TOLERANCE)]
                    matching_po = self.env['purchase.order'].search(purchase_id_domain)
                    if len(matching_po) == 1:
                        self._set_purchase_orders(matching_po)
            else:
                matching_pos_invoice_lines = [{
                    'purchase_order': matching_po,
                    'line': line,
                    'amount_to_invoice': (1 - line.qty_invoiced / line.product_qty) * line.price_total,
                } for matching_po in matching_pos for line in matching_po.mapped('order_line') if line.product_qty]
                if total_ocr - TOLERANCE < sum(line['amount_to_invoice'] for line in matching_pos_invoice_lines) < total_ocr + TOLERANCE:
                    self._set_purchase_orders(matching_pos)
                else:
                    il_subset = self.find_matching_subset_invoice_lines(matching_pos_invoice_lines, total_ocr)
                    if il_subset:
                        self._set_purchase_orders(set(line['purchase_order'] for line in il_subset))
                        subset_purchase_order_line_ids = set(line['line'] for line in il_subset)
                        with self._get_edi_creation() as move_form:
                            for line in move_form.invoice_line_ids:
                                if line.purchase_line_id and line.purchase_line_id not in subset_purchase_order_line_ids:
                                    line.quantity = 0
                    else:
                        self._set_purchase_orders(matching_pos)
        return super(AccountMove, self)._save_form(ocr_results, force_write=force_write)
