# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import re
import datetime

from PyPDF2 import PdfFileReader, PdfFileWriter

from odoo import models
from odoo.http import request, route, Controller, content_disposition
from odoo.tools.safe_eval import safe_eval


class HrPayroll(Controller):

    @route(["/print/payslips"], type='http', auth='user')
    def get_payroll_report_print(self, list_ids='', **post):
        if not request.env.user.has_group('hr_payroll.group_hr_payroll_user') or not list_ids or re.search("[^0-9|,]", list_ids):
            return request.not_found()

        ids = [int(s) for s in list_ids.split(',')]
        payslips = request.env['hr.payslip'].browse(ids)

        pdf_writer = PdfFileWriter()

        for payslip in payslips:
            if not payslip.struct_id or not payslip.struct_id.report_id:
                report = request.env.ref('hr_payroll.action_report_payslip', False)
            else:
                report = payslip.struct_id.report_id
            pdf_content, _ = request.env['ir.actions.report'].\
                with_context(lang=payslip.employee_id.sudo().address_home_id.lang).\
                sudo().\
                _render_qweb_pdf(report, payslip.id, data={'company_id': payslip.company_id})
            reader = PdfFileReader(io.BytesIO(pdf_content), strict=False, overwriteWarnings=False)

            for page in range(reader.getNumPages()):
                pdf_writer.addPage(reader.getPage(page))

        _buffer = io.BytesIO()
        pdf_writer.write(_buffer)
        merged_pdf = _buffer.getvalue()
        _buffer.close()

        if len(payslips) == 1 and payslips.struct_id.report_id.print_report_name:
            report_name = safe_eval(payslips.struct_id.report_id.print_report_name, {'object': payslips})
        else:
            report_name = "Payslips"

        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(merged_pdf)),
            ('Content-Disposition', content_disposition(report_name + '.pdf'))
        ]

        return request.make_response(merged_pdf, headers=pdfhttpheaders)

    @route(["/debug/payslip/<int:payslip_id>"], type='http', auth='user')
    def get_debug_script_for_incorrect_payslip(self, payslip_id):
        """
        Generate a python file containing all useful data in setUp method of a
        unit test to reproduce the exact situation of the employee and compute the same payslip.
        """
        if not request.env.user._is_superuser():
            return request.not_found()

        payslip = request.env['hr.payslip'].browse(int(payslip_id))

        if not payslip.exists():
            return request.not_found()

        start = datetime.datetime(payslip.date_from.year, payslip.date_from.month, payslip.date_from.day)
        end = datetime.datetime(payslip.date_to.year, payslip.date_to.month, payslip.date_to.day, 23, 59, 59)

        # Convert several record into a list of dictionaries containing the record values
        def _records_to_values(records, whitelisted_fields, forced_values):
            result = []
            for record in records:
                record_vals = forced_values.copy()
                for field_name, value in record.fields_get().items():
                    if not value['store'] or field_name == 'id' or field_name not in whitelisted_fields:
                        continue
                    if field_name in forced_values.keys():
                        record_vals[field_name] = forced_values[field_name]
                    elif field_name.endswith('_ids'):
                        record_vals[field_name] = record[field_name].ids
                    elif (field_name.endswith('_id') or field_name.endswith('_uid')):
                        record_vals[field_name] = _record_to_xmlid_ref(record[field_name]) or record[field_name].id
                    else:
                        record_vals[field_name] = record[field_name]
                result.append(record_vals)
            return result

        # Convert dict in str while replacing references to newly created record on the python
        # method (example: employee_id: cls.employee.id)
        def _vals_list_to_string(vals_list, offset=0):
            result = []
            for vals in vals_list:
                vals_strings = []
                for key, value in vals.items():
                    if key.endswith('_id') and isinstance(value, str):
                        value = value
                    elif isinstance(value, datetime.date) and isinstance(value, datetime.datetime):  # datetime only
                        value = "datetime.datetime(%s, %s, %s, %s, %s, %s)" % (value.year, value.month, value.day, value.hour, value.minute, value.second)
                    elif isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):  # date only
                        value = "datetime.date(%s, %s, %s)" % (value.year, value.month, value.day)
                    elif not isinstance(value, str):
                        value = str(value)
                    else:
                        value = '"%s"' % (str(value))
                    vals_strings.append("\t" * (offset + 1) + "'%s': %s" % (key, value))
                result.append(',\n'.join(vals_strings))
            return ("\n" + "\t" * offset + "}, {\n").join(result)

        def _record_to_xmlid_ref(record):
            if not record:
                return ''
            return "cls.env.ref('%s').id" % record.get_external_id()[record.id]

        offset = 1  # useful to correctly indent python file
        content_py_file = [
            "# -*- coding:utf-8 -*-",
            "# Part of Odoo. See LICENSE file for full copyright and licensing details.\n",
            # imports
            "import datetime",
            "from odoo.addons.account.tests.common import AccountTestInvoicingCommon",
            "from odoo.tests.common import tagged\n\n",

            # class for the unit test
            "@tagged('post_install', '-at_install', 'sample_payslip')",
            "class TestSamplePayslip(AccountTestInvoicingCommon):\n",
            # setUp method for the unit test
            "\t" * offset + "@classmethod",
            "\t" * offset + "def setUpClass(cls, chart_template_ref='l10n_be.l10nbe_chart_template'):",
        ]

        offset += 1
        content_py_file += [
            "\t" * offset + "super().setUpClass(chart_template_ref=chart_template_ref)\n",
            "\t" * offset + "cls.company_data['company'].country_id.code = 'BE'\n",
            "\t" * offset + "cls.env.user.tz = 'Europe/Brussels'\n",
        ]

        # ===============
        # PRIVATE ADDRESS
        # ===============
        address = payslip.employee_id.address_home_id
        address_name = 'address_home'
        address_fields = []
        address_forced_values = {
            'name': 'Test Employee',
            'company_id': "cls.env.company.id",
            'type': 'private'
        }

        # ========
        # CALENDAR
        # ========
        calendar = payslip.employee_id.resource_calendar_id
        calendar_name = 'resource_calendar'
        calendar_fields = [
            'hours_per_day', 'tz', 'two_weeks_calendar', 'hours_per_week',
            'full_time_required_hours']
        calendar_forced_values = {
            'name': 'Test Calendar',
            'company_id': "cls.env.company.id",
            'attendance_ids': [(5, 0, 0)],
        }

        # ===========
        # ATTENDANCES
        # ===========
        # Take all global attendances + employee attendances (TODO: Filter dates)
        global_attendances = payslip.employee_id.resource_calendar_id.attendance_ids.filtered(
            lambda a: not a.resource_id)
        global_attendances_name = 'global_attendances'
        global_attendances_fields = [
            'name', 'dayofweek', 'date_from', 'date_to', 'hour_from', 'hour_to', 'day_period',
            'resource_id', 'week_type', 'display_type', 'sequence', 'work_entry_type_id'
        ]
        global_attendances_forced_values = {
            'name': 'Attendance',
            'calendar_id': "cls.resource_calendar.id",
        }

        # ======
        # Leaves
        # ======
        global_leaves = payslip.employee_id.resource_calendar_id.leave_ids.filtered(
            lambda a: not a.resource_id and start <= a.date_to and end >= a.date_from)
        global_leaves_name = 'leaves'
        global_leaves_fields = [
            'date_from', 'date_to', 'resource_id', 'time_type', 'work_entry_type_id', 'display_name',
        ]
        global_leaves_forced_values = {
            'name': 'Absence',
            'calendar_id': "cls.resource_calendar.id",
            'company_id': "cls.env.company.id",
        }

        # ========
        # EMPLOYEE
        # ========
        employee = payslip.employee_id
        employee_name = 'employee'
        employee_fields = [
            'marital', 'children', 'km_home_work', 'spouse_fiscal_status', 'disabled', 'disabled_spouse_bool',
            'disabled_children_bool', 'resident_bool', 'disabled_children_number', 'other_dependent_people',
            'other_senior_dependent', 'other_disabled_senior_dependent', 'other_juniors_dependent',
            'other_disabled_juniors_dependent', 'has_bicycle']
        employee_forced_values = {
            'name': 'Test Employee',
            'address_home_id': "cls.address_home.id",
            'resource_calendar_id': "cls.resource_calendar.id",
            'company_id': "cls.env.company.id",
        }

        # ====================
        # EMPLOYEE ATTENDANCES
        # ====================
        attendances = payslip.employee_id.resource_calendar_id.attendance_ids.filtered(
            lambda a: a.resource_id == payslip.employee_id.resource_id)
        attendances_name = 'attendances'
        attendances_fields = global_attendances_fields
        attendances_forced_values = {**global_attendances_forced_values, **{'resource_id': "cls.employee.resource_id.id"}}

        # ===============
        # EMPLOYEE LEAVES
        # ===============
        leaves = payslip.employee_id.resource_calendar_id.leave_ids.filtered(
            lambda a: a.resource_id == payslip.employee_id.resource_id and start <= a.date_to and end >= a.date_from)
        leaves_name = 'leaves'
        leaves_fields = global_leaves_fields
        leaves_forced_values = {**global_leaves_forced_values, **{'resource_id': "cls.employee.resource_id.id"}}

        # ===========
        # COMPANY CAR
        # ===========
        if 'car_id' in payslip.contract_id:
            # BRAND
            brand = payslip.contract_id.car_id.model_id.brand_id
            brand_name = 'brand'
            brand_fields = []
            brand_forced_values = {'name': 'Test Brand'}

            # MODEL
            model = payslip.contract_id.car_id.model_id
            model_name = 'model'
            model_fields = ['name', 'vehicle_type']
            model_forced_values = {
                'name': 'Test Model',
                'brand_id': "cls.brand.id",
            }

            # CAR
            car = payslip.contract_id.car_id
            car_name = 'car'
            car_fields = [
                'first_contract_date', 'co2', 'car_value', 'fuel_type', 'acquisition_date'
            ]
            car_forced_values = {
                'name': 'Test Car',
                'license_plate': 'TEST',
                'driver_id': "cls.employee.address_home_id.id",
                'company_id': "cls.env.company.id",
                'model_id': "cls.model.id",
            }

            # CAR CONTRACTS
            car_contracts = payslip.contract_id.car_id.log_contracts.filtered(lambda c: c.state == 'open')
            car_contracts_name = 'contracts'
            car_contracts_fields = [
                'start_date', 'expiration_date', 'state', 'cost_generated', 'cost_frequency',
                'recurring_cost_amount_depreciated',
            ]
            car_contracts_forced_values = {
                'name': 'Test Contract',
                'vehicle_id': "cls.car.id",
                'company_id': "cls.env.company.id",
            }
        else:
            brand, brand_name, brand_fields, brand_forced_values = None, None, None, None
            model, model_name, model_fields, model_forced_values = None, None, None, None
            car, car_name, car_fields, car_forced_values = None, None, None, None
            car_contracts, car_contracts_name, car_contracts_fields, car_contracts_forced_values = None, None, None, None

        # ========
        # Contract
        # ========
        if 'time_credit' in payslip.contract_id and payslip.contract_id.time_credit:
            standard_calendar = payslip.contract_id.standard_calendar_id
            standard_calendar_name = 'standard_calendar'
            standard_calendar_fields = calendar_fields
            standard_calendar_forced_values = {
                'name': 'Test Standard Calendar',
                'company_id': "cls.env.company.id",
                'attendance_ids': [(5, 0, 0)],
            }

            standard_calendar_attendances = standard_calendar.attendance_ids.filtered(lambda a: not a.resource_id)
            standard_calendar_attendances_name = 'standard_calendar_attendances'
            standard_calendar_attendances_fields = global_attendances_fields
            standard_calendar_attendances_forced_values = {
                'name': 'Attendance',
                'calendar_id': "cls.standard_calendar.id",
            }
        else:
            standard_calendar, standard_calendar_name, standard_calendar_fields, standard_calendar_forced_values = None, None, None, None
            standard_calendar_attendances, standard_calendar_attendances_name, standard_calendar_attendances_fields, standard_calendar_attendances_forced_values = None, None, None, None

        contract = payslip.contract_id
        contract_name = 'contract'
        contract_fields = [
            'date_start', 'date_end', 'wage', 'state', 'wage_type', 'hourly_wage', 'holidays',
            'transport_mode_car', 'transport_mode_private_car', 'transport_mode_train',
            'transport_mode_public', 'train_transport_employee_amount',
            'public_transport_employee_amount', 'km_home_work',
            'commission_on_target', 'fuel_card', 'internet', 'representation_fees', 'mobile',
            'has_laptop', 'meal_voucher_amount', 'eco_checks', 'ip', 'ip_wage_rate', 'time_credit',
            'work_time_rate', 'fiscal_voluntarism', 'fiscal_voluntary_rate',
            'structure_type_id',
        ]
        contract_forced_values = {
            'name': "Contract For Payslip Test",
            'employee_id': "cls.employee.id",
            'resource_calendar_id': "cls.resource_calendar.id",
            'company_id': "cls.env.company.id",
            'date_generated_from': start, # to avoid generating too many work entries
            'date_generated_to': start,
        }
        if car:
            contract_forced_values['car_id'] = "cls.car.id"
        if standard_calendar:
            contract_forced_values['standard_calendar_id'] = "cls.standard_calendar.id"

        # =======
        # PAYSLIP
        # =======
        payslip_name = 'payslip'
        payslip_fields = ['date_from', 'date_to', 'struct_id', 'struct_type_id']
        payslip_forced_values = {
            'name': "Test Payslip",
            'employee_id': "cls.employee.id",
            'contract_id': "cls.contract.id",
            'company_id': "cls.env.company.id",
        }

        if car:
            payslip_forced_values['vehicle_id'] = "cls.car.id"

        # ======
        # Inputs
        # ======
        inputs = payslip.input_line_ids
        inputs_name = 'inputs'
        inputs_fields = ['sequence', 'input_type_id', 'amount']
        inputs_forced_values = {
            'name': 'Test Input',
            'payslip_id': 'cls.payslip.id',
        }

        # ==============
        # EXPORT RECORDS
        # ==============

        data_to_export = [
            (address, address_name, address_fields, address_forced_values),
            (calendar, calendar_name, calendar_fields, calendar_forced_values),
            (global_attendances, global_attendances_name, global_attendances_fields, global_attendances_forced_values),
            (global_leaves, global_leaves_name, global_leaves_fields, global_leaves_forced_values),
            (employee, employee_name, employee_fields, employee_forced_values),
            (attendances, attendances_name, attendances_fields, attendances_forced_values),
            (leaves, leaves_name, leaves_fields, leaves_forced_values),
            (brand, brand_name, brand_fields, brand_forced_values),
            (model, model_name, model_fields, model_forced_values),
            (car, car_name, car_fields, car_forced_values),
            (car_contracts, car_contracts_name, car_contracts_fields, car_contracts_forced_values),
            (standard_calendar, standard_calendar_name, standard_calendar_fields, standard_calendar_forced_values),
            (standard_calendar_attendances, standard_calendar_attendances_name, standard_calendar_attendances_fields, standard_calendar_attendances_forced_values),
            (contract, contract_name, contract_fields, contract_forced_values),
            (payslip, payslip_name, payslip_fields, payslip_forced_values),
            (inputs, inputs_name, inputs_fields, inputs_forced_values),
        ]

        for records, name, whitelisted_fields, forced_values in data_to_export:
            if not records:
                continue
            records_values = _records_to_values(records, whitelisted_fields, forced_values)
            content_py_file += [
                "%(offset)scls.%(name)s = cls.env['%(model)s'].create([{" % {
                    'offset': "\t" * offset,
                    'name': name,
                    'model': records._name},
                _vals_list_to_string(records_values, offset),
                "\t" * offset + "}])\n"
            ]

        offset -= 1

        # ==========
        # WRITE TEST
        # ==========
        content_py_file.append("\t" * offset + "def test_sample_payslip(self):")
        offset += 1
        content_py_file += [
            "\t" * offset + "work_entries = self.contract._generate_work_entries(datetime.date(%s, %s, %s), datetime.date(%s, %s, %s))" % (
                start.year, start.month, start.day, end.year, end.month, end.day),
            "\t" * offset + "work_entries.action_validate()",
            "\t" * offset + "self.payslip.compute_sheet()\n",
        ] + [
            "\t" * offset + "self.assertEqual(len(self.payslip.worked_days_line_ids), %s)" % (len(payslip.worked_days_line_ids)),
            "\t" * offset + "self.assertEqual(len(self.payslip.input_line_ids), %s)" % (len(payslip.input_line_ids)),
            "\t" * offset + "self.assertEqual(len(self.payslip.line_ids), %s)\n" % (len(payslip.line_ids)),
        ] + [
            "\t" * offset + "self.assertAlmostEqual(self.payslip._get_worked_days_line_amount('%s'), %s, places=2)" % (
                wd.code, wd.amount) for wd in payslip.worked_days_line_ids
        ] + [''] + [
            "\t" * offset + "self.assertAlmostEqual(self.payslip._get_worked_days_line_number_of_days('%s'), %s, places=2)" % (
                wd.code, wd.number_of_days) for wd in payslip.worked_days_line_ids
        ] + [''] + [
            "\t" * offset + "self.assertAlmostEqual(self.payslip._get_worked_days_line_number_of_hours('%s'), %s, places=2)" % (
                wd.code, wd.number_of_hours) for wd in payslip.worked_days_line_ids
        ] + [''] + [
            "\t" * offset + "self.assertAlmostEqual(self.payslip._get_salary_line_total('%s'), %s, places=2)" % (
                line.code, line.total) for line in payslip.line_ids
        ]

        script = "\n".join(content_py_file) + '\n'  # take all content to create the script
        script = script.replace("\t", ' ' * 4)  # replace each tab by 4 whitespaces

        # ===========
        # EXPORT FILE
        # ===========

        http_headers = [
            ('Content-Type', 'application/text'),
            ('Content-Length', len(script)),
            ('Content-Disposition', 'attachment; filename=test.py;')
        ]
        return request.make_response(script, headers=http_headers)
