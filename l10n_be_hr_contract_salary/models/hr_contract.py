# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    id_card = fields.Binary(related='employee_id.id_card', groups="hr_contract.group_hr_contract_manager")
    driving_license = fields.Binary(related='employee_id.driving_license', groups="hr_contract.group_hr_contract_manager")
    mobile_invoice = fields.Binary(related='employee_id.mobile_invoice', groups="hr_contract.group_hr_contract_manager")
    sim_card = fields.Binary(related='employee_id.sim_card', groups="hr_contract.group_hr_contract_manager")
    internet_invoice = fields.Binary(related="employee_id.internet_invoice", groups="hr_contract.group_hr_contract_manager")
    double_holiday_wage = fields.Monetary(compute='_compute_double_holiday_wage')
    contract_type_id = fields.Many2one('hr.contract.type', "Contract Type",
                                       default=lambda self: self.env.ref('l10n_be_hr_payroll.l10n_be_contract_type_cdi',
                                                                         raise_if_not_found=False))
    has_bicycle = fields.Boolean(related="employee_id.has_bicycle")
    l10n_be_bicyle_cost = fields.Float(compute='_compute_l10n_be_bicyle_cost')

    @api.depends('employee_id.has_bicycle', 'employee_id.has_bicycle')
    def _compute_l10n_be_bicyle_cost(self):
        for contract in self:
            if not contract.employee_id.has_bicycle:
                contract.l10n_be_bicyle_cost = 0
            else:
                contract.l10n_be_bicyle_cost = self._get_private_bicycle_cost(contract.employee_id.km_home_work)

    @api.model
    def _get_private_bicycle_cost(self, distance):
        amount_per_km = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('cp200_cycle_reimbursement_per_km', raise_if_not_found=False) or 0.20
        amount_max = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('cp200_cycle_reimbursement_max', raise_if_not_found=False) or 8
        return 52 * min(amount_max, amount_per_km * distance * 2)

    @api.depends(
        'wage_with_holidays', 'wage_on_signature', 'state',
        'employee_id.l10n_be_scale_seniority', 'job_id.l10n_be_scale_category',
        'work_time_rate', 'time_credit', 'resource_calendar_id.work_time_rate')
    def _compute_l10n_be_is_below_scale(self):
        super()._compute_l10n_be_is_below_scale()

    @api.depends('wage_with_holidays')
    def _compute_double_holiday_wage(self):
        for contract in self:
            contract.double_holiday_wage = contract.wage_with_holidays * 0.92

    def _get_redundant_salary_data(self):
        res = super()._get_redundant_salary_data()
        cars = self.mapped('car_id').filtered(lambda car: not car.active and not car.license_plate)
        vehicle_contracts = cars.with_context(active_test=False).mapped('log_contracts').filtered(
            lambda contract: not contract.active)
        return res + [cars, vehicle_contracts]

    @api.model
    def _advantage_white_list(self):
        return super()._advantage_white_list() + [
            'private_car_reimbursed_amount',
            'yearly_commission_cost',
            'meal_voucher_average_monthly_amount',
        ]

    def _get_advantage_values_company_car_total_depreciated_cost(self, contract, advantages):
        has_car = advantages['fold_company_car_total_depreciated_cost']
        selected_car = advantages['select_company_car_total_depreciated_cost']
        if not has_car or not selected_car:
            return {
                'transport_mode_car': False,
                'new_car': False,
                'new_car_model_id': False,
                'car_id': False,
            }
        car, car_id = selected_car.split('-')
        new_car = car == 'new'
        if new_car:
            return {
                'transport_mode_car': True,
                'new_car': True,
                'new_car_model_id': int(car_id),
                'car_id': False,
            }
        return {
            'transport_mode_car': True,
            'new_car': False,
            'new_car_model_id': False,
            'car_id': int(car_id),
        }

    def _get_advantage_values_company_bike_depreciated_cost(self, contract, advantages):
        has_bike = advantages['fold_company_bike_depreciated_cost']
        selected_bike = advantages.get('select_company_bike_depreciated_cost', None)
        if not has_bike or not selected_bike:
            return {
                'transport_mode_bike': False,
                'new_bike_model_id': False,
                'bike_id': False,
            }
        bike, bike_id = selected_bike.split('-')
        new_bike = bike == 'new'
        if new_bike:
            return {
                'transport_mode_bike': True,
                'new_bike_model_id': int(bike_id),
                'bike_id': False,
            }
        return {
            'transport_mode_bike': True,
            'new_bike_model_id': False,
            'bike_id': int(bike_id),
        }

    def _get_advantage_values_wishlist_car_total_depreciated_cost(self, contract, advantages):
        # make sure the key `fold_wishlist_car_total_depreciated_cost` is present, super() needs it
        advantages['fold_wishlist_car_total_depreciated_cost'] = advantages.get('fold_wishlist_car_total_depreciated_cost')
        return {}

    def _get_advantage_values_insured_relative_spouse(self, contract, advantages):
        return {'insured_relative_spouse': advantages['fold_insured_relative_spouse']}

    def _get_advantage_values_l10n_be_ambulatory_insured_spouse(self, contract, advantages):
        return {'l10n_be_ambulatory_insured_spouse': advantages['fold_l10n_be_ambulatory_insured_spouse']}

    def _get_description_company_car_total_depreciated_cost(self, new_value=None):
        advantage = self.env.ref('l10n_be_hr_contract_salary.l10n_be_transport_company_car')
        description = advantage.description
        if new_value is None or not new_value:
            if self.car_id:
                new_value = 'old-%s' % self.car_id.id
            elif self.new_car_model_id:
                new_value = 'new-%s' % self.new_car_model_id.id
            else:
                return description
        car_option, vehicle_id = new_value.split('-')
        try:
            vehicle_id = int(vehicle_id)
        except:
            return description
        if car_option == "new":
            vehicle = self.env['fleet.vehicle.model'].sudo().browse(vehicle_id)
            co2 = vehicle.default_co2
            fuel_type = vehicle.default_fuel_type
            transmission = vehicle.transmission
            door_number = odometer = immatriculation = trailer_hook = False
        else:
            vehicle = self.env['fleet.vehicle'].sudo().browse(vehicle_id)
            co2 = vehicle.co2
            fuel_type = vehicle.fuel_type
            door_number = vehicle.doors
            odometer = vehicle.odometer
            immatriculation = vehicle.acquisition_date
            transmission = vehicle.transmission
            trailer_hook = "Yes" if vehicle.trailer_hook else "No"
        car_elements = {
            'CO2 Emission': co2,
            'Fuel Type': fuel_type,
            'Transmission': transmission,
            'Doors Number': door_number,
            'Trailer Hook': trailer_hook,
            'Odometer': odometer,
            'Immatriculation Date': immatriculation
        }
        description += '<ul>%s</ul>' % ''.join(['<li>%s: %s</li>' % (key, value) for key, value in car_elements.items() if value])
        return description

    def _get_description_commission_on_target(self, new_value=None):
        self.ensure_one()
        return '<span class="form-text">The commission is scalable and starts from the 1st € sold. The commission plan has stages with accelerators. At 100%%, 3 months are paid in Warrant which results to a monthly NET commission value of %s € and 9 months in cash which result in a GROSS monthly commission of %s €, taxable like your usual monthly pay.</span>' % (round(self.warrant_value_employee, 2), round(self.commission_on_target, 2))

    def _get_advantage_values_ip_value(self, contract, advantages):
        if not advantages['ip_value'] or not ast.literal_eval(advantages['ip_value']):
            return {
                'ip': False,
                'ip_wage_rate': contract.ip_wage_rate
            }
        return {
            'ip': True,
            'ip_wage_rate': contract.ip_wage_rate
        }
