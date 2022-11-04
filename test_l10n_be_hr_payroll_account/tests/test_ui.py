# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import time

from freezegun import freeze_time

import odoo.tests
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.modules.module import get_module_resource


@odoo.tests.tagged('-at_install', 'post_install', 'salary')
class TestUi(odoo.tests.HttpCase):
    def test_ui(self):
        # no user available for belgian company so to set hr responsible change company of demo
        demo = mail_new_test_user(self.env, name="Laurie Poiret", login='be_demo', groups='hr.group_hr_user,sign.group_sign_user')
        pdf_path = get_module_resource('hr_contract_salary', 'static', 'src', 'demo', 'employee_contract.pdf')
        pdf_content = base64.b64encode(open(pdf_path, "rb").read())

        attachment = self.env['ir.attachment'].create({
            'type': 'binary',
            'datas': pdf_content,
            'name': 'test_employee_contract.pdf',
        })
        template = self.env['sign.template'].create({
            'attachment_id': attachment.id,
            'sign_item_ids': [(6, 0, [])],
        })

        self.env['sign.item'].create([
            {
                'type_id': self.env.ref('sign.sign_item_type_text').id,
                'name': 'employee_id.name',
                'required': True,
                'responsible_id': self.env.ref('sign.sign_item_role_employee').id,
                'page': 1,
                'posX': 0.273,
                'posY': 0.158,
                'template_id': template.id,
                'width': 0.150,
                'height': 0.015,
            }, {
                'type_id': self.env.ref('sign.sign_item_type_date').id,
                'name': False,
                'required': True,
                'responsible_id': self.env.ref('sign.sign_item_role_employee').id,
                'page': 1,
                'posX': 0.707,
                'posY': 0.158,
                'template_id': template.id,
                'width': 0.150,
                'height': 0.015,
            }, {
                'type_id': self.env.ref('sign.sign_item_type_text').id,
                'name': 'employee_id.address_home_id.city',
                'required': True,
                'responsible_id': self.env.ref('sign.sign_item_role_employee').id,
                'page': 1,
                'posX': 0.506,
                'posY': 0.184,
                'template_id': template.id,
                'width': 0.150,
                'height': 0.015,
            }, {
                'type_id': self.env.ref('sign.sign_item_type_text').id,
                'name': 'employee_id.address_home_id.country_id.name',
                'required': True,
                'responsible_id': self.env.ref('sign.sign_item_role_employee').id,
                'page': 1,
                'posX': 0.663,
                'posY': 0.184,
                'template_id': template.id,
                'width': 0.150,
                'height': 0.015,
            }, {
                'type_id': self.env.ref('sign.sign_item_type_text').id,
                'name': 'employee_id.address_home_id.street2',
                'required': True,
                'responsible_id': self.env.ref('sign.sign_item_role_employee').id,
                'page': 1,
                'posX': 0.349,
                'posY': 0.184,
                'template_id': template.id,
                'width': 0.150,
                'height': 0.015,
            }, {
                'type_id': self.env.ref('sign.sign_item_type_signature').id,
                'name': False,
                'required': True,
                'responsible_id': self.env.ref('hr_contract_sign.sign_item_role_job_responsible').id,
                'page': 2,
                'posX': 0.333,
                'posY': 0.575,
                'template_id': template.id,
                'width': 0.200,
                'height': 0.050,
            }, {
                'type_id': self.env.ref('sign.sign_item_type_signature').id,
                'name': False,
                'required': True,
                'responsible_id': self.env.ref('sign.sign_item_role_employee').id,
                'page': 2,
                'posX': 0.333,
                'posY': 0.665,
                'template_id': template.id,
                'width': 0.200,
                'height': 0.050,
            }, {
                'type_id': self.env.ref('sign.sign_item_type_date').id,
                'name': False,
                'required': True,
                'responsible_id': self.env.ref('sign.sign_item_role_employee').id,
                'page': 2,
                'posX': 0.665,
                'posY': 0.694,
                'template_id': template.id,
                'width': 0.150,
                'height': 0.015,
            }
        ])

        company_id = self.env['res.company'].create({
            'name': 'My Belgian Company - TEST',
            'country_id': self.env.ref('base.be').id,
        })
        partner_id = self.env['res.partner'].create({
            'name': 'Laurie Poiret',
            'street': '58 rue des Wallons',
            'city': 'Louvain-la-Neuve',
            'zip': '1348',
            'country_id': self.env.ref("base.be").id,
            'phone': '+0032476543210',
            'email': 'laurie.poiret@example.com',
            'company_id': company_id.id,
        })

        bike_brand = self.env['fleet.vehicle.model.brand'].create({
            'name': 'Bike Brand',
        })

        self.env['fleet.vehicle.model'].with_company(company_id).create({
            'name': 'Bike 1',
            'brand_id': bike_brand.id,
            'vehicle_type': 'bike',
            'can_be_requested': True,
            'default_car_value': 1000,
            'default_recurring_cost_amount_depreciated': 25,
        })

        self.env['fleet.vehicle.model'].with_company(company_id).create({
            'name': 'Bike 2',
            'brand_id': bike_brand.id,
            'vehicle_type': 'bike',
            'can_be_requested': True,
            'default_car_value': 2000,
            'default_recurring_cost_amount_depreciated': 50,
        })
        model_a3 = self.env.ref("fleet.model_a3").with_company(company_id)
        model_a3.default_recurring_cost_amount_depreciated = 450
        model_a3.can_be_requested = True

        model_opel = self.env.ref("fleet.model_corsa").with_company(company_id)
        model_opel.can_be_requested = True

        self.env['fleet.vehicle'].create({
            'model_id': model_a3.id,
            'license_plate': '1-JFC-095',
            'acquisition_date': time.strftime('%Y-01-01'),
            'co2': 88,
            'driver_id': partner_id.id,
            'plan_to_change_car': True,
            'car_value': 38000,
            'company_id': company_id.id,
        })

        a_recv = self.env['account.account'].create({
            'code': 'X1012',
            'name': 'Debtors - (test)',
            'reconcile': True,
            'account_type': 'asset_receivable',
        })
        a_pay = self.env['account.account'].create({
            'code': 'X1111',
            'name': 'Creditors - (test)',
            'account_type': 'liability_payable',
            'reconcile': True,
        })
        self.env['ir.property']._set_default(
            'property_account_receivable_id',
            'res.partner',
            a_recv,
            company_id,
        )
        self.env['ir.property']._set_default(
            'property_account_payable_id',
            'res.partner',
            a_pay,
            company_id,
        )

        self.env.ref('base.user_admin').write({'company_ids': [(4, company_id.id)], 'name': 'Mitchell Admin'})
        self.env.ref('base.user_admin').partner_id.write({'email': 'mitchell.stephen@example.com', 'name': 'Mitchell Admin'})
        demo.write({'partner_id': partner_id, 'company_id': company_id.id, 'company_ids': [(4, company_id.id)]})

        contract_template = self.env['hr.contract'].create({
            'name': 'New Developer Template Contract',
            'wage': 3000,
            'structure_type_id': self.env.ref('hr_contract.structure_type_employee_cp200').id,
            'ip_wage_rate': 25,
            'sign_template_id': template.id,
            'contract_update_template_id': template.id,
            'hr_responsible_id': self.env.ref('base.user_admin').id,
            'company_id': company_id.id,
            'representation_fees': 150,
            'meal_voucher_amount': 7.45,
            'fuel_card': 0,
            'internet': 38,
            'mobile': 30,
            'eco_checks': 250,
            'car_id': False
        })

        self.env.flush_all()
        with freeze_time("2022-01-01"):
            self.start_tour("/", 'hr_contract_salary_tour', login='admin', timeout=300)

        new_contract_id = self.env['hr.contract'].search([('name', 'ilike', 'nathalie')])
        self.assertTrue(new_contract_id, 'A contract has been created')
        new_employee_id = new_contract_id.employee_id
        self.assertTrue(new_employee_id, 'An employee has been created')
        self.assertFalse(new_employee_id.active, 'Employee is not yet active')

        model_corsa = self.env.ref("fleet.model_corsa")
        vehicle = self.env['fleet.vehicle'].search([('company_id', '=', company_id.id), ('model_id', '=', model_corsa.id)])
        self.assertFalse(vehicle, 'A vehicle has not been created')

        self.start_tour("/", 'hr_contract_salary_tour_hr_sign', login='admin', timeout=300)

        # Contract is signed by new employee and HR, the new car must be created
        vehicle = self.env['fleet.vehicle'].search([('company_id', '=', company_id.id), ('model_id', '=', model_corsa.id)])
        self.assertTrue(vehicle, 'A vehicle has been created')
        self.assertEqual(vehicle.future_driver_id, new_employee_id.address_home_id, 'Futur driver is set')
        self.assertEqual(vehicle.state_id, self.env.ref('fleet.fleet_vehicle_state_new_request'), 'Car created in right state')
        self.assertEqual(vehicle.company_id, new_contract_id.company_id, 'Vehicle is in the right company')
        self.assertTrue(new_employee_id.active, 'Employee is now active')

        # they are a new limit to available car: 1. In the new contract, we can choose to be in waiting list.
        self.env['ir.config_parameter'].sudo().set_param('l10n_be_hr_payroll_fleet.max_unused_cars', 1)

        self.start_tour("/", 'hr_contract_salary_tour_2', login='admin', timeout=300)
        new_contract_id = self.env['hr.contract'].search([('name', 'ilike', 'Mitchell Admin 3')])
        self.assertTrue(new_contract_id, 'A contract has been created')
        new_employee_id = new_contract_id.employee_id
        self.assertTrue(new_employee_id, 'An employee has been created')
        self.assertTrue(new_employee_id.active, 'Employee is active')

        vehicle = self.env['fleet.vehicle'].search([('future_driver_id', '=', new_employee_id.address_home_id.id)])
        self.assertTrue(vehicle, 'A vehicle has been created')
        self.assertEqual(vehicle.model_id, model_a3, 'Car is right model')
        self.assertEqual(vehicle.state_id, self.env.ref('fleet.fleet_vehicle_state_waiting_list'), 'Car created in right state')
        self.assertEqual(vehicle.company_id, new_contract_id.company_id, 'Vehicle is in the right company')
