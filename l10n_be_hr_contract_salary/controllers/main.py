# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import fields, _
from odoo.addons.hr_contract_salary.controllers import main
from odoo.addons.sign.controllers.main import Sign
from odoo.http import route, request

ODOMETER_UNITS = {'kilometers': 'km', 'miles': 'mi'}

class SignContract(Sign):

    def _update_contract_on_signature(self, request_item, contract):
        super()._update_contract_on_signature(request_item, contract)
        # Only the applicant/employee has signed
        if request_item.sign_request_id.nb_closed == 1 and contract.car_id:
            if contract.car_id and contract.driver_id != contract.employee_id.address_home_id:
                contract.car_id.future_driver_id = contract.employee_id.address_home_id
        # Both applicant/employee and HR responsible have signed
        if request_item.sign_request_id.nb_closed == 2:
            if contract.new_car or contract.new_bike_model_id:
                state_new_request = request.env.ref('fleet.fleet_vehicle_state_new_request', raise_if_not_found=False)
                Vehicle = request.env['fleet.vehicle'].sudo()
                vehicle_vals = {
                    'state_id': state_new_request and state_new_request.id,
                    'future_driver_id': contract.employee_id.address_home_id.id,
                    'company_id': contract.company_id.id,
                }
                contracts_vals = {
                    'cost_frequency': 'no',
                    'purchaser_id': contract.employee_id.address_home_id.id,
                }
            if contract.new_car:
                model = contract.new_car_model_id.sudo()
                contract.update({
                    'new_car': False,
                    'new_car_model_id': False,
                })
                contract.car_id = Vehicle.create(dict(vehicle_vals, **{
                    'model_id': model.id,
                    'car_value': model.default_car_value,
                    'co2': model.default_co2,
                    'fuel_type': model.default_fuel_type,
                }))
                vehicle_contract = contract.car_id.log_contracts[0]
                vehicle_contract.write(dict(contracts_vals , **{
                    'recurring_cost_amount_depreciated': model.default_recurring_cost_amount_depreciated,
                    'cost_generated': model.default_recurring_cost_amount_depreciated,
                }))
            if contract.new_bike_model_id:
                contract.update({
                    'new_bike': False,
                    'new_bike_model_id': False,
                })
                model = contract.new_bike_model_id.sudo()
                contract.bike_id = Vehicle.create(dict(vehicle_vals, **{
                    'model_id': model.id,
                    'car_value': model.default_car_value,
                    'co2': model.default_co2,
                    'fuel_type': model.default_fuel_type,
                }))
                vehicle_contract = contract.bike_id.log_contracts[0]
                vehicle_contract.write(dict(contracts_vals , **{
                    'recurring_cost_amount_depreciated': model.default_recurring_cost_amount_depreciated,
                    'cost_generated': model.default_recurring_cost_amount_depreciated,
                }))

class HrContractSalary(main.HrContractSalary):

    @route(['/salary_package/simulation/contract/<int:contract_id>'], type='http', auth="public", website=True)
    def salary_package(self, contract_id=None, **kw):
        contract = request.env['hr.contract'].sudo().browse(contract_id)

        if contract._get_work_time_rate() == 0:
            return request.render('http_routing.http_error', {'status_code': _('Oops'),
                                                         'status_message': _('This contract is a full time credit time... No simulation can be done for this type of contract as its wage is equal to 0.')})
        return super(HrContractSalary, self).salary_package(contract_id, **kw)

    @route(['/salary_package/onchange_advantage'], type='json', auth='public')
    def onchange_advantage(self, advantage_field, new_value, contract_id, advantages):
        res = super().onchange_advantage(advantage_field, new_value, contract_id, advantages)
        insurance_fields = [
            'insured_relative_children', 'insured_relative_adults',
            'fold_insured_relative_spouse', 'has_hospital_insurance']
        ambulatory_insurance_fields = [
            'l10n_be_ambulatory_insured_children', 'l10n_be_ambulatory_insured_adults',
            'fold_l10n_be_ambulatory_insured_spouse', 'l10n_be_has_ambulatory_insurance']
        if advantage_field == "km_home_work":
            new_value = new_value if new_value else 0
            res['extra_values'] = [
                ('private_car_reimbursed_amount_manual', new_value),
                ('l10n_be_bicyle_cost_manual', new_value),
                ('l10n_be_bicyle_cost', round(request.env['hr.contract']._get_private_bicycle_cost(float(new_value)), 2) if advantages['contract']['fold_l10n_be_bicyle_cost'] else 0),
                ('private_car_reimbursed_amount', round(request.env['hr.contract']._get_private_car_reimbursed_amount(float(new_value)), 2)  if advantages['contract']['fold_private_car_reimbursed_amount'] else 0),
            ]
        if advantage_field == 'public_transport_reimbursed_amount':
            res['new_value'] = round(request.env['hr.contract']._get_public_transport_reimbursed_amount(float(new_value)), 2)
        elif advantage_field == 'train_transport_reimbursed_amount':
            res['new_value'] = round(request.env['hr.contract']._get_train_transport_reimbursed_amount(float(new_value)), 2)
        elif advantage_field == 'private_car_reimbursed_amount':
            new_value = new_value if new_value else 0
            res['new_value'] = round(request.env['hr.contract']._get_private_car_reimbursed_amount(float(new_value)), 2)
            res['extra_values'] = [
                ('km_home_work', new_value),
                ('l10n_be_bicyle_cost_manual', new_value),
                ('l10n_be_bicyle_cost', round(request.env['hr.contract']._get_private_bicycle_cost(float(new_value)), 2) if advantages['contract']['fold_l10n_be_bicyle_cost'] else 0),
            ]
        elif advantage_field == 'ip_value':
            contract = self._check_access_rights(contract_id)
            res['new_value'] = contract.ip_wage_rate if float(new_value) else 0
        elif advantage_field in ['company_car_total_depreciated_cost', 'company_bike_depreciated_cost'] and new_value:
            car_options, vehicle_id = new_value.split('-')
            if car_options == 'new':
                res['new_value'] = round(request.env['fleet.vehicle.model'].sudo().browse(int(vehicle_id)).default_total_depreciated_cost, 2)
            else:
                res['new_value'] = round(request.env['fleet.vehicle'].sudo().browse(int(vehicle_id)).total_depreciated_cost, 2)
        elif advantage_field == 'wishlist_car_total_depreciated_cost':
            res['new_value'] = 0
        elif advantage_field == 'fold_company_car_total_depreciated_cost' and not res['new_value']:
            res['extra_values'] = [('company_car_total_depreciated_cost', 0)]
        elif advantage_field == 'fold_wishlist_car_total_depreciated_cost' and not res['new_value']:
            res['extra_values'] = [('wishlist_car_total_depreciated_cost', 0)]
        elif advantage_field == 'fold_company_bike_depreciated_cost' and not res['new_value']:
            res['extra_values'] = [('company_bike_depreciated_cost', 0)]
        elif advantage_field in insurance_fields:
            child_amount = float(request.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.hospital_insurance_amount_child', default=7.2))
            adult_amount = float(request.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.hospital_insurance_amount_adult', default=20.5))
            adv = advantages['contract']
            child_count = int(adv['insured_relative_children_manual'] or False)
            has_hospital_insurance = float(adv['has_hospital_insurance_radio']) == 1.0 if 'has_hospital_insurance_radio' in adv else False
            adult_count = int(adv['insured_relative_adults_manual'] or False) + int(adv['fold_insured_relative_spouse']) + int(has_hospital_insurance)
            insurance_amount = request.env['hr.contract']._get_insurance_amount(child_amount, child_count, adult_amount, adult_count)
            res['extra_values'] = [('has_hospital_insurance', insurance_amount)]
        if advantage_field in ambulatory_insurance_fields:
            child_amount = float(request.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.ambulatory_insurance_amount_child', default=7.2))
            adult_amount = float(request.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.ambulatory_insurance_amount_adult', default=20.5))
            adv = advantages['contract']
            child_count = int(adv['l10n_be_ambulatory_insured_children_manual'] or False)
            l10n_be_has_ambulatory_insurance = float(adv['l10n_be_has_ambulatory_insurance_radio']) == 1.0 if 'l10n_be_has_ambulatory_insurance_radio' in adv else False
            adult_count = int(adv['l10n_be_ambulatory_insured_adults_manual'] or False) \
                        + int(adv['fold_l10n_be_ambulatory_insured_spouse']) \
                        + int(l10n_be_has_ambulatory_insurance)
            insurance_amount = request.env['hr.contract']._get_insurance_amount(
                child_amount, child_count,
                adult_amount, adult_count)
            res['extra_values'] = [('l10n_be_has_ambulatory_insurance', insurance_amount)]
        if advantage_field == 'l10n_be_bicyle_cost':
            new_value = new_value if new_value else 0
            res['new_value'] = round(request.env['hr.contract']._get_private_bicycle_cost(float(new_value)), 2)
            res['extra_values'] = [
                ('km_home_work', new_value),
                ('private_car_reimbursed_amount_manual', new_value),
                ('private_car_reimbursed_amount', round(request.env['hr.contract']._get_private_car_reimbursed_amount(float(new_value)), 2)  if advantages['contract']['fold_private_car_reimbursed_amount'] else 0),
            ]
        if advantage_field == 'fold_l10n_be_bicyle_cost':
            distance = advantages['employee']['km_home_work'] or '0'
            res['extra_values'] = [('l10n_be_bicyle_cost', round(request.env['hr.contract']._get_private_bicycle_cost(float(distance)), 2) if advantages['contract']['fold_l10n_be_bicyle_cost'] else 0)]
        if advantage_field == 'fold_private_car_reimbursed_amount':
            distance = advantages['employee']['km_home_work'] or '0'
            res['extra_values'] = [('private_car_reimbursed_amount', round(request.env['hr.contract']._get_private_car_reimbursed_amount(float(distance)), 2)  if advantages['contract']['fold_private_car_reimbursed_amount'] else 0)]
        return res

    def _apply_url_value(self, contract, field_name, value):
        if field_name == 'l10n_be_canteen_cost':
            return {'l10n_be_canteen_cost': value}
        return super()._apply_url_value(contract, field_name, value)

    def _get_default_template_values(self, contract):
        values = super()._get_default_template_values(contract)
        values['l10n_be_canteen_cost'] = False
        return values

    def _get_advantages(self, contract):
        res = super()._get_advantages(contract)
        force_new_car = request.httprequest.args.get('new_car', False)
        if request.params.get('applicant_id') or force_new_car or contract.available_cars_amount < contract.max_unused_cars:
            res -= request.env.ref('l10n_be_hr_contract_salary.l10n_be_transport_new_car')
        return res

    def _get_advantages_values(self, contract):
        mapped_advantages, advantage_types, dropdown_options, dropdown_group_options, initial_values = super()._get_advantages_values(contract)

        available_cars = request.env['fleet.vehicle'].sudo().search(
            contract._get_available_vehicles_domain(contract.employee_id.address_home_id)).sorted(key=lambda car: car.total_depreciated_cost)
        available_bikes = request.env['fleet.vehicle'].sudo().search(
            contract._get_available_vehicles_domain(contract.employee_id.address_home_id, vehicle_type='bike')).sorted(key=lambda car: car.total_depreciated_cost)
        force_car = request.httprequest.args.get('car_id', False)
        force_car_id = False
        if int(force_car):
            force_car_id = request.env['fleet.vehicle'].sudo().browse(int(force_car))
            available_cars |= force_car_id

        def generate_dropdown_group_data(available, can_be_requested, only_new, allow_new_cars, vehicle_type='Car'):
            # Creates the necessary data for the dropdown group, looks like this
            # {
            #     'category_name': [
            #         (value, value),
            #         (value, value),...
            #     ],
            #     'other_category': ...
            # }
            model_categories = (available.model_id.category_id | can_be_requested.category_id)
            model_categories_ids = model_categories.sorted(key=lambda c: (c.sequence, c.id)).ids
            model_categories_ids.append(0) # Case when no category
            result = OrderedDict()
            for category in model_categories_ids:
                category_id = model_categories.filtered(lambda c: c.id == category)
                car_values = []
                if not only_new:
                    cars = available.filtered_domain([
                        ('model_id.category_id', '=', category),
                    ])
                    car_values.extend([(
                        'old-%s' % (car.id),
                        '%s/%s \u2022 %s € \u2022 %s%s%s' % (
                            car.model_id.brand_id.name,
                            car.model_id.name,
                            round(car.total_depreciated_cost, 2),
                            car._get_acquisition_date() if vehicle_type == 'Car' else '',
                            _('\u2022 Available in %s', car.next_assignation_date.strftime('%B %Y')) if car.next_assignation_date else u'',
                            ' \u2022 %s %s' % (car.odometer, ODOMETER_UNITS[car.odometer_unit]) if vehicle_type == 'Car' else '',
                        )
                    ) for car in cars])

                if allow_new_cars:
                    requestables = can_be_requested.filtered_domain([
                        ('category_id', '=', category)
                    ])
                    car_values.extend([(
                        'new-%s' % (model.id),
                        '%s \u2022 %s € \u2022 New %s' % (
                            model.display_name,
                            round(model.default_total_depreciated_cost, 2),
                            vehicle_type,
                        )
                    ) for model in requestables])

                if car_values:
                    result[category_id.name or _("No Category")] = car_values
            return result

        def generate_dropdown_data(available, can_be_requested, only_new_cars, allow_new_cars, vehicle_type='Car'):
            result = []
            if not only_new_cars:
                result.extend([(
                    'old-%s' % (car.id),
                    '%s/%s \u2022 %s € \u2022 %s%s%s' % (
                        car.model_id.brand_id.name,
                        car.model_id.name,
                        round(car.total_depreciated_cost, 2),
                        car._get_acquisition_date() if vehicle_type == 'Car' else '',
                        _('\u2022 Available in %s', car.next_assignation_date.strftime('%B %Y')) if car.next_assignation_date else u'',
                        ' \u2022 %s %s' % (car.odometer, ODOMETER_UNITS[car.odometer_unit]) if vehicle_type == 'Car' else '',
                    )
                ) for car in available])
            if allow_new_cars:
                result.extend([(
                    'new-%s' % (model.id),
                    '%s \u2022 %s € \u2022 New %s' % (
                        model.display_name,
                        round(model.default_total_depreciated_cost, 2),
                        vehicle_type,
                    )
                ) for model in can_be_requested_models])
            return result

        advantages = self._get_advantages(contract)
        car_advantage = advantages.filtered(
            lambda a: a.res_field_id.name == 'company_car_total_depreciated_cost'
        )
        bike_advantage = advantages.filtered(
            lambda a: a.res_field_id.name == 'company_bike_depreciated_cost'
        )
        wishlist_car_advantage = advantages.filtered(
            lambda a: a.res_field_id.name == 'wishlist_car_total_depreciated_cost'
        )

        # Car stuff
        can_be_requested_models = request.env['fleet.vehicle.model'].sudo().with_company(contract.company_id).search(
        contract._get_possible_model_domain()).sorted(key=lambda model: model.default_total_depreciated_cost)

        force_new_car = request.httprequest.args.get('new_car', False)
        allow_new_cars = False
        wishlist_new_cars = False
        if force_new_car or contract.available_cars_amount < contract.max_unused_cars:
            allow_new_cars = True
        else:
            wishlist_new_cars = True

        if car_advantage.display_type == 'dropdown-group':
            dropdown_group_options['company_car_total_depreciated_cost'] = \
                generate_dropdown_group_data(available_cars, can_be_requested_models, False, allow_new_cars)
        else:
            dropdown_options['company_car_total_depreciated_cost'] = \
                generate_dropdown_data(available_cars, can_be_requested_models, False, allow_new_cars)

        if wishlist_new_cars:
            if wishlist_car_advantage.display_type == 'dropdown-group':
                dropdown_group_options['wishlist_car_total_depreciated_cost'] = \
                    generate_dropdown_group_data(available_cars, can_be_requested_models, True, True)
            else:
                dropdown_options['wishlist_car_total_depreciated_cost'] = \
                    generate_dropdown_data(available_cars, can_be_requested_models, True, True)
            initial_values['fold_wishlist_car_total_depreciated_cost'] = False
            initial_values['wishlist_car_total_depreciated_cost'] = 0

        # Bike stuff
        can_be_requested_models = request.env['fleet.vehicle.model'].sudo().with_company(contract.company_id).search(
        contract._get_possible_model_domain(vehicle_type='bike')).sorted(key=lambda model: model.default_total_depreciated_cost)
        if bike_advantage.display_type == 'dropdown-group':
            dropdown_group_options['company_bike_depreciated_cost'] = \
                generate_dropdown_group_data(available_bikes, can_be_requested_models, False, True, 'Bike')
        else:
            dropdown_options['company_bike_depreciated_cost'] = \
                generate_dropdown_data(available_bikes, can_be_requested_models, False, True, 'Bike')


        if force_car_id:
            initial_values['select_company_car_total_depreciated_cost'] = 'old-%s' % force_car_id.id
            initial_values['fold_company_car_total_depreciated_cost'] = True
            initial_values['company_car_total_depreciated_cost'] = force_car_id.total_depreciated_cost
        elif contract.car_id:
            initial_values['select_company_car_total_depreciated_cost'] = 'old-%s' % contract.car_id.id
            initial_values['fold_company_car_total_depreciated_cost'] = True
            initial_values['company_car_total_depreciated_cost'] = contract.car_id.total_depreciated_cost
        elif contract.new_car_model_id:
            initial_values['select_company_car_total_depreciated_cost'] = 'new-%s' % contract.new_car_model_id.id
            initial_values['fold_company_car_total_depreciated_cost'] = True
            initial_values['company_car_total_depreciated_cost'] = contract.new_car_model_id.default_total_depreciated_cost
        else:
            initial_values['fold_company_car_total_depreciated_cost'] = False
        if contract.bike_id:
            initial_values['select_company_bike_depreciated_cost'] = 'old-%s' % contract.bike_id.id
        elif contract.new_bike_model_id:
            initial_values['select_company_bike_depreciated_cost'] = 'new-%s' % contract.new_bike_model_id.id

        initial_values['has_hospital_insurance'] = contract.insurance_amount
        initial_values['l10n_be_has_ambulatory_insurance'] = contract.l10n_be_ambulatory_insurance_amount

        return mapped_advantages, advantage_types, dropdown_options, dropdown_group_options, initial_values

    def _get_new_contract_values(self, contract, employee, advantages):
        res = super()._get_new_contract_values(contract, employee, advantages)
        fields_to_copy = [
            'has_laptop', 'time_credit', 'work_time_rate',
            'rd_percentage', 'no_onss', 'no_withholding_taxes'
        ]
        for field_to_copy in fields_to_copy:
            if field_to_copy in contract:
                res[field_to_copy] = contract[field_to_copy]
        res['has_hospital_insurance'] = float(advantages['has_hospital_insurance_radio']) == 1.0 if 'has_hospital_insurance_radio' in advantages else False
        res['l10n_be_has_ambulatory_insurance'] = float(advantages['l10n_be_has_ambulatory_insurance_radio']) == 1.0 if 'l10n_be_has_ambulatory_insurance_radio' in advantages else False
        res['l10n_be_canteen_cost'] = advantages['l10n_be_canteen_cost']
        return res

    def create_new_contract(self, contract, advantages, no_write=False, **kw):
        new_contract, contract_diff = super().create_new_contract(contract, advantages, no_write=no_write, **kw)
        if new_contract.time_credit:
            new_contract.date_end = contract.date_end
        if kw.get('package_submit', False):
            # If the chosen existing car is already taken by someone else (for example if the
            # window was open for a long time)
            if new_contract.transport_mode_car and not new_contract.new_car:
                available_cars_domain = new_contract._get_available_vehicles_domain(new_contract.employee_id.address_home_id)
                if new_contract.car_id not in request.env['fleet.vehicle'].sudo().search(available_cars_domain):
                    return {'error': True, 'error_msg': _("Sorry, the selected car has been selected by someone else. Please refresh and try again.")}

            # Don't create simulation cars but create the wishlist car is set
            wishlist_car = advantages['contract'].get('fold_wishlist_car_total_depreciated_cost', False)
            if wishlist_car:
                dummy, model_id = advantages['contract']['select_wishlist_car_total_depreciated_cost'].split('-')
                model = request.env['fleet.vehicle.model'].sudo().browse(int(model_id))
                state_waiting_list = request.env.ref('fleet.fleet_vehicle_state_waiting_list', raise_if_not_found=False)
                car = request.env['fleet.vehicle'].sudo().create({
                    'model_id': model.id,
                    'state_id': state_waiting_list and state_waiting_list.id,
                    'car_value': model.default_car_value,
                    'co2': model.default_co2,
                    'fuel_type': model.default_fuel_type,
                    'acquisition_date': new_contract.car_id.acquisition_date or fields.Date.today(),
                    'company_id': new_contract.company_id.id,
                    'future_driver_id': new_contract.employee_id.address_home_id.id
                })
                vehicle_contract = car.log_contracts[0]
                vehicle_contract.recurring_cost_amount_depreciated = model.default_recurring_cost_amount_depreciated
                vehicle_contract.cost_generated = model.default_recurring_cost_amount_depreciated
                vehicle_contract.cost_frequency = 'no'
                vehicle_contract.purchaser_id = new_contract.employee_id.address_home_id.id
            return new_contract, contract_diff

        if new_contract.transport_mode_car and new_contract.new_car:
            employee = new_contract.employee_id
            model = new_contract.new_car_model_id
            state_new_request = request.env.ref('fleet.fleet_vehicle_state_new_request', raise_if_not_found=False)
            new_contract.car_id = request.env['fleet.vehicle'].sudo().create({
                'model_id': model.id,
                'state_id': state_new_request and state_new_request.id,
                'driver_id': employee.address_home_id.id,
                'car_value': model.default_car_value,
                'co2': model.default_co2,
                'fuel_type': model.default_fuel_type,
                'company_id': new_contract.company_id.id,
            })
            vehicle_contract = new_contract.car_id.log_contracts[0]
            vehicle_contract.recurring_cost_amount_depreciated = model.default_recurring_cost_amount_depreciated
            vehicle_contract.cost_generated = model.default_recurring_cost_amount_depreciated
            vehicle_contract.cost_frequency = 'no'
            vehicle_contract.purchaser_id = employee.address_home_id.id
        return new_contract, contract_diff

    def _get_compute_results(self, new_contract):
        result = super()._get_compute_results(new_contract)
        result['double_holiday_wage'] = round(new_contract.double_holiday_wage, 2)
        # Horrible hack: Add a sequence / display condition fields on salary resume model in master
        resume = result['resume_lines_mapped']['Monthly Salary']
        if 'SALARY' in resume and resume.get('wage_with_holidays') and resume['wage_with_holidays'][1] != resume['SALARY'][1]:
            ordered_fields = ['wage_with_holidays', 'SALARY', 'NET']
        else:
            ordered_fields = ['wage_with_holidays', 'NET']
        result['resume_lines_mapped']['Monthly Salary'] = {field: resume.get(field, 0) for field in ordered_fields}
        return result

    def _generate_payslip(self, new_contract):
        payslip = super()._generate_payslip(new_contract)
        if new_contract.car_id:
            payslip.vehicle_id = new_contract.car_id
        if new_contract.commission_on_target:
            payslip.input_line_ids = [(0, 0, {
                'input_type_id': request.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': new_contract.commission_on_target,
            })]
        return payslip

    def _get_payslip_line_values(self, payslip, codes):
        res = super()._get_payslip_line_values(payslip, codes + ['BASIC', 'COMMISSION'])
        res['SALARY'][payslip.id]['total'] = res['BASIC'][payslip.id]['total'] + res['COMMISSION'][payslip.id]['total']
        return res

    def _get_personal_infos_langs(self, contract, personal_info):
        active_langs = super()._get_personal_infos_langs(contract, personal_info)
        personal_info_lang = request.env.ref('l10n_be_hr_contract_salary.hr_contract_salary_personal_info_lang')
        if contract.structure_type_id.country_id.code == 'BE' and personal_info == personal_info_lang:
            belgian_langs = active_langs.filtered(lambda l: l.code in ["fr_BE", "fr_FR", "nl_BE", "nl_NL", "de_BE", "de_DE"])
            return active_langs if not belgian_langs else belgian_langs
        return active_langs
