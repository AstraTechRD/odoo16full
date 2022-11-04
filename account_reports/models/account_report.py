# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import datetime
import io
import json
import logging
import math
import re
import base64
from ast import literal_eval
from collections import defaultdict
from functools import cmp_to_key

import markupsafe
from babel.dates import get_quarter_names
from dateutil.relativedelta import relativedelta

from odoo.addons.web.controllers.utils import clean_action
from odoo import models, fields, api, _, osv
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import config, date_utils, get_lang, float_compare, float_is_zero
from odoo.tools.float_utils import float_round
from odoo.tools.misc import formatLang, format_date, xlsxwriter
from odoo.tools.safe_eval import expr_eval, safe_eval
from odoo.models import check_method_name

_logger = logging.getLogger(__name__)

ACCOUNT_CODES_ENGINE_SPLIT_REGEX = re.compile(r"(?=[+-])")

ACCOUNT_CODES_ENGINE_TERM_REGEX = re.compile(
    r"^(?P<sign>[+-]?)"\
    r"(?P<prefix>[A-Za-z\d.]*((?=\\)|(?<=[^CD])))"\
    r"(\\\((?P<excluded_prefixes>([A-Za-z\d.]+,)*[A-Za-z\d.]*)\))?"\
    r"(?P<balance_character>[DC]?)$"
)


class AccountReportManager(models.Model):
    _name = 'account.report.manager'
    _description = 'Manage Summary and Footnotes of Reports'

    # must work with multi-company, in case of multi company, no company_id defined
    report_name = fields.Char(required=True, help='name of the model of the report')
    summary = fields.Char()
    footnotes_ids = fields.One2many('account.report.footnote', 'manager_id')
    company_id = fields.Many2one('res.company')
    report_id = fields.Many2one(comodel_name='account.report')

    def add_footnote(self, text, line):
        return self.env['account.report.footnote'].create({'line': line, 'text': text, 'manager_id': self.id})

class AccountReportFootnote(models.Model):
    _name = 'account.report.footnote'
    _description = 'Account Report Footnote'

    text = fields.Char()
    line = fields.Char(index=True)
    manager_id = fields.Many2one('account.report.manager')

class AccountReport(models.Model):
    _inherit = 'account.report'

    # Templates
    # Those fields aren't relational, so that their values can be used in t-call in the xml templates
    main_template = fields.Char(string="Main Template", required=True, default='account_reports.main_template')
    main_table_header_template = fields.Char(string="Main Table Header Template", required=True, default='account_reports.main_table_header')
    line_template = fields.Char(string="Line Template", required=True, default='account_reports.line_template')
    footnotes_template = fields.Char(string="Footnotes Template", required=True, default='account_reports.footnotes_template')
    search_template = fields.Char(string="Search Template", required=True, default='account_reports.search_template')
    horizontal_group_ids = fields.Many2many(string="Horizontal Groups", comodel_name='account.report.horizontal.group')

    #  CUSTOM REPORTS ================================================================================================================================
    # Those fields allow case-by-case fine-tuning of the engine, for custom reports.

    custom_handler_model_id = fields.Many2one(string='Custom Handler Model', comodel_name='ir.model')
    custom_handler_model_name = fields.Char(string='Custom Handler Model Name', related='custom_handler_model_id.model')

    @api.constrains('custom_handler_model_id')
    def _validate_custom_handler_model(self):
        for report in self:
            if report.custom_handler_model_id:
                custom_handler_model = self.env['account.report.custom.handler']
                current_model = self.env[report.custom_handler_model_name]
                if not isinstance(current_model, type(custom_handler_model)):
                    raise ValidationError(_(
                        "Field 'Custom Handler Model' can only reference records inheriting from [%s].",
                        custom_handler_model._name
                    ))

    @api.constrains('main_template', 'main_table_header_template', 'line_template', 'footnotes_template', 'search_template')
    def _validate_templates(self):
        for record in self:
            for template_field in ['main_template', 'main_table_header_template', 'line_template', 'footnotes_template', 'search_template']:
                template_xmlid = record[template_field]
                if not self.env.ref(template_xmlid, raise_if_not_found=False):
                    raise ValidationError(_("Could not find template %s, used as %s of %s.", template_xmlid, template_field, record.name))

    ####################################################
    # MENU MANAGEMENT
    ####################################################

    def _create_menu_item_for_report(self):
        """ Adds a default menu item for this report. This is called by an action on the report, for reports created manually by the user.
        """
        self.ensure_one()

        action = self.env['ir.actions.client'].create({
            'name': self.name,
            'tag': 'account_report',
            'context': {'report_id': self.id},
        })

        menu_item_vals = {
            'name': self.name,
            'parent_id': self.env['ir.model.data']._xmlid_to_res_id('account.menu_finance_reports'),
            'action': f'ir.actions.client,{action.id}',
        }

        self.env['ir.ui.menu'].create(menu_item_vals)

    ####################################################
    # OPTIONS: journals
    ####################################################

    def _get_filter_journals(self, options, additional_domain=None):
        return self.env['account.journal'].with_context(active_test=False).search([
                ('company_id', 'in', [comp['id'] for comp in options.get('multi_company', self.env.company)]),
                *(additional_domain or []),
            ], order="company_id, name")

    def _get_filter_journal_groups(self, options, report_accepted_journals):
        groups = self.env['account.journal.group'].search([
            ('company_id', 'in', [comp['id'] for comp in options.get('multi_company', self.env.company)]),
            ], order='sequence')

        all_journals = self._get_filter_journals(options)
        all_journals_by_company = {}
        for journal in all_journals:
            all_journals_by_company.setdefault(journal.company_id, self.env['account.journal'])
            all_journals_by_company[journal.company_id] += journal

        ret = self.env['account.journal.group']
        for journal_group in groups:
            # Only display the group if the journals it could accept are all accepted by this report
            group_accepted_journals = all_journals_by_company[journal_group.company_id] - journal_group.excluded_journal_ids
            if not group_accepted_journals - report_accepted_journals:
                ret += journal_group
        return ret

    def _init_options_journals(self, options, previous_options=None, additional_journals_domain=None):
        # The additional additional_journals_domain optinal parameter allows calling this with an additional restriction on journals,
        # to regenerate the journal options accordingly.

        if not self.filter_journals:
            return

        # Collect all stuff and split them by company.
        all_journals = self._get_filter_journals(options, additional_domain=additional_journals_domain)
        all_journal_groups = self._get_filter_journal_groups(options, all_journals)
        all_journal_ids = set(all_journals.ids)

        per_company_map = {}
        for company in self.env.companies:
            per_company_map[company] = ({
                'available_journals': self.env['account.journal'],
                'available_journal_groups': self.env['account.journal.group'],
                'selected_journals': self.env['account.journal'],
                'selected_journal_groups': self.env['account.journal.group'],
            })

        for journal in all_journals:
            per_company_map[journal.company_id]['available_journals'] |= journal
        for journal_group in all_journal_groups:
            per_company_map[journal_group.company_id]['available_journal_groups'] |= journal_group

        # Adapt the code from previous options.
        journal_group_action = None
        if previous_options:
            # Reload from previous options.
            if previous_options.get('journals'):
                for journal_opt in previous_options['journals']:
                    if journal_opt.get('model') == 'account.journal' and journal_opt.get('selected'):
                        journal_id = int(journal_opt['id'])
                        if journal_id in all_journal_ids:
                            journal = self.env['account.journal'].browse(journal_id)
                            per_company_map[journal.company_id]['selected_journals'] |= journal

            # Process the action performed by the user js-side.
            journal_group_action = previous_options.get('__journal_group_action', None)
            if journal_group_action:
                action = journal_group_action['action']
                group = self.env['account.journal.group'].browse(journal_group_action['id'])
                company_vals = per_company_map[group.company_id]
                if action == 'add':
                    remaining_journals = company_vals['available_journals'] - group.excluded_journal_ids
                    company_vals['selected_journals'] = remaining_journals
                elif action == 'remove':
                    has_selected_journal_in_other_company = False
                    for company, other_company_vals in per_company_map.items():
                        if company == group.company_id:
                            continue

                        if other_company_vals['selected_journals']:
                            has_selected_journal_in_other_company = True
                            break

                    if has_selected_journal_in_other_company:
                        company_vals['selected_journals'] = company_vals['available_journals']
                    else:
                        company_vals['selected_journals'] = self.env['account.journal']

                    # When removing the last selected group in multi-company, make sure there is no selected journal left.
                    # For example, suppose company1 having j1, j2 as journals and group1 excluding j2, company2 having j3, j4.
                    # Suppose group1, j1, j3, j4 selected. If group1 is removed, we need to unselect j3 and j4 as well.
                    if all(x['selected_journals'] == x['available_journals'] for x in per_company_map.values()):
                        for company_vals in per_company_map.values():
                            company_vals['selected_journals'] = self.env['account.journal']
        else:
            # Select the first available group if nothing selected.
            has_selected_at_least_one_group = False
            for company in self.env.companies:
                company_vals = per_company_map[company]
                if not company_vals['selected_journals'] and company_vals['available_journal_groups']:
                    first_group = company_vals['available_journal_groups'][0]
                    remaining_journals = company_vals['available_journals'] - first_group.excluded_journal_ids
                    company_vals['selected_journals'] = remaining_journals
                    has_selected_at_least_one_group = True

            # Select all journals in others groups.
            if has_selected_at_least_one_group:
                for company, company_vals in per_company_map.items():
                    if not company_vals['selected_journals']:
                        company_vals['selected_journals'] = company_vals['available_journals']

        # Build the options.
        journal_groups_options = []
        journal_options_per_company = defaultdict(list)
        for company, company_vals in per_company_map.items():
            company_vals = per_company_map[company]

            # Groups.
            for group in company_vals['available_journal_groups']:
                remaining_journals = company_vals['available_journals'] - company_vals['selected_journals']
                selected = remaining_journals == (group.excluded_journal_ids & company_vals['available_journals'])
                journal_groups_options.append({
                    'id': group.id,
                    'model': group._name,
                    'name': group.display_name,
                    'selected': selected,
                    'journal_types': set(remaining_journals.mapped('type')),
                })
                if selected:
                    company_vals['selected_journal_groups'] |= group

            # Journals.
            for journal in company_vals['available_journals']:
                journal_options_per_company[journal.company_id].append({
                    'id': journal.id,
                    'model': journal._name,
                    'name': journal.display_name,
                    'title': f"{journal.name} - {journal.code}",
                    'selected': journal in company_vals['selected_journals'],
                    'type': journal.type,
                })

        # Build the final options.
        options['journals'] = []
        if journal_groups_options:
            options['journals'].append({
                'id': 'divider',
                'name': _("Journal Groups"),
                'model': 'account.journal.group',
            })
            options['journals'] += journal_groups_options
        for company, journal_options in journal_options_per_company.items():
            if len(journal_options_per_company) > 1 or journal_groups_options:
                options['journals'].append({
                    'id': 'divider',
                    'model': company._name,
                    'name': company.display_name,
                })
            options['journals'] += journal_options

        # Compute the name to display on the widget.
        names_to_display = []

        has_globally_selected_groups = False
        has_selected_all_journals = True
        for company, journal_options in per_company_map.items():
            for journal_group in journal_options['selected_journal_groups']:
                names_to_display.append(journal_group.display_name)
                has_globally_selected_groups = True
            if journal_options['selected_journals'] != journal_options['available_journals']:
                has_selected_all_journals = False

        for company, journal_options in per_company_map.items():
            has_selected_groups = bool(journal_options['selected_journal_groups'])
            if not has_selected_groups and (not has_selected_all_journals or has_globally_selected_groups):
                for journal in journal_options['selected_journals']:
                    names_to_display.append(journal.code)

        if not names_to_display:
            names_to_display.append(_("All Journals"))
            for journal_option in options['journals']:
                if journal_option.get('model') == 'account.journal':
                    journal_option['selected'] = False

        # Abbreviate the name
        max_nb_journals_displayed = 5
        nb_remaining = len(names_to_display) - max_nb_journals_displayed
        if nb_remaining == 1:
            options['name_journal_group'] = ', '.join(names_to_display[:max_nb_journals_displayed]) + _(" and one other")
        elif nb_remaining > 1:
            options['name_journal_group'] = ', '.join(names_to_display[:max_nb_journals_displayed]) + _(" and %s others", nb_remaining)
        else:
            options['name_journal_group'] = ', '.join(names_to_display)

    @api.model
    def _get_options_journals(self, options):
        selected_journals = [
            journal for journal in options.get('journals', [])
            if not journal['id'] in ('divider', 'group') and journal['selected']
        ]
        if not selected_journals:
            # If no journal is specifically selected, we actually want to select them all.
            # This is needed, because some reports will not use ALL available journals and filter by type.
            # Without getting them from the options, we will use them all, which is wrong.
            selected_journals = [
                journal for journal in options.get('journals', []) if
                not journal['id'] in ('divider', 'group')
            ]
        return selected_journals

    @api.model
    def _get_options_journals_domain(self, options):
        # Make sure to return an empty array when nothing selected to handle archived journals.
        selected_journals = self._get_options_journals(options)
        return selected_journals and [('journal_id', 'in', [j['id'] for j in selected_journals])] or []

    ####################################################
    # OPTIONS: date + comparison
    ####################################################

    @api.model
    def _get_dates_period(self, date_from, date_to, mode, period_type=None):
        '''Compute some information about the period:
        * The name to display on the report.
        * The period type (e.g. quarter) if not specified explicitly.
        :param date_from:   The starting date of the period.
        :param date_to:     The ending date of the period.
        :param period_type: The type of the interval date_from -> date_to.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type * mode *
        '''
        def match(dt_from, dt_to):
            return (dt_from, dt_to) == (date_from, date_to)

        string = None
        # If no date_from or not date_to, we are unable to determine a period
        if not period_type or period_type == 'custom':
            date = date_to or date_from
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date)
            if match(company_fiscalyear_dates['date_from'], company_fiscalyear_dates['date_to']):
                period_type = 'fiscalyear'
                if company_fiscalyear_dates.get('record'):
                    string = company_fiscalyear_dates['record'].name
            elif match(*date_utils.get_month(date)):
                period_type = 'month'
            elif match(*date_utils.get_quarter(date)):
                period_type = 'quarter'
            elif match(*date_utils.get_fiscal_year(date)):
                period_type = 'year'
            elif match(date_utils.get_month(date)[0], fields.Date.today()):
                period_type = 'today'
            else:
                period_type = 'custom'
        elif period_type == 'fiscalyear':
            date = date_to or date_from
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date)
            record = company_fiscalyear_dates.get('record')
            string = record and record.name

        if not string:
            fy_day = self.env.company.fiscalyear_last_day
            fy_month = int(self.env.company.fiscalyear_last_month)
            if mode == 'single':
                string = _('As of %s') % (format_date(self.env, fields.Date.to_string(date_to)))
            elif period_type == 'year' or (
                    period_type == 'fiscalyear' and (date_from, date_to) == date_utils.get_fiscal_year(date_to)):
                string = date_to.strftime('%Y')
            elif period_type == 'fiscalyear' and (date_from, date_to) == date_utils.get_fiscal_year(date_to, day=fy_day, month=fy_month):
                string = '%s - %s' % (date_to.year - 1, date_to.year)
            elif period_type == 'month':
                string = format_date(self.env, fields.Date.to_string(date_to), date_format='MMM yyyy')
            elif period_type == 'quarter':
                quarter_names = get_quarter_names('abbreviated', locale=get_lang(self.env).code)
                string = u'%s\N{NO-BREAK SPACE}%s' % (
                    quarter_names[date_utils.get_quarter_number(date_to)], date_to.year)
            else:
                dt_from_str = format_date(self.env, fields.Date.to_string(date_from))
                dt_to_str = format_date(self.env, fields.Date.to_string(date_to))
                string = _('From %s\nto  %s') % (dt_from_str, dt_to_str)

        return {
            'string': string,
            'period_type': period_type,
            'mode': mode,
            'date_from': date_from and fields.Date.to_string(date_from) or False,
            'date_to': fields.Date.to_string(date_to),
        }

    @api.model
    def _get_dates_previous_period(self, options, period_vals):
        '''Shift the period to the previous one.
        :param period_vals: A dictionary generated by the _get_dates_period method.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type *
        '''
        period_type = period_vals['period_type']
        mode = period_vals['mode']
        date_from = fields.Date.from_string(period_vals['date_from'])
        date_to = date_from - datetime.timedelta(days=1)

        if period_type in ('fiscalyear', 'today'):
            # Don't pass the period_type to _get_dates_period to be able to retrieve the account.fiscal.year record if
            # necessary.
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date_to)
            return self._get_dates_period(company_fiscalyear_dates['date_from'], company_fiscalyear_dates['date_to'], mode)
        if period_type in ('month', 'custom'):
            return self._get_dates_period(*date_utils.get_month(date_to), mode, period_type='month')
        if period_type == 'quarter':
            return self._get_dates_period(*date_utils.get_quarter(date_to), mode, period_type='quarter')
        if period_type == 'year':
            return self._get_dates_period(*date_utils.get_fiscal_year(date_to), mode, period_type='year')
        return None

    @api.model
    def _get_dates_previous_year(self, options, period_vals):
        '''Shift the period to the previous year.
        :param options:     The report options.
        :param period_vals: A dictionary generated by the _get_dates_period method.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type *
        '''
        period_type = period_vals['period_type']
        mode = period_vals['mode']
        date_from = fields.Date.from_string(period_vals['date_from'])
        date_from = date_from - relativedelta(years=1)
        date_to = fields.Date.from_string(period_vals['date_to'])
        date_to = date_to - relativedelta(years=1)

        if period_type == 'month':
            date_from, date_to = date_utils.get_month(date_to)
        return self._get_dates_period(date_from, date_to, mode, period_type=period_type)

    def _init_options_date(self, options, previous_options=None):
        """ Initialize the 'date' options key.

        :param options:             The current report options to build.
        :param previous_options:    The previous options coming from another report.
        """
        previous_date = (previous_options or {}).get('date', {})
        previous_date_to = previous_date.get('date_to')
        previous_date_from = previous_date.get('date_from')
        previous_mode = previous_date.get('mode')
        previous_filter = previous_date.get('filter', 'custom')

        default_filter = self.default_opening_date_filter
        options_mode = 'range' if self.filter_date_range else 'single'
        date_from = date_to = period_type = False

        if previous_mode == 'single' and options_mode == 'range':
            # 'single' date mode to 'range'.

            if previous_filter:
                date_to = fields.Date.from_string(previous_date_to or previous_date_from)
                date_from = self.env.company.compute_fiscalyear_dates(date_to)['date_from']
                options_filter = 'custom'
            else:
                options_filter = default_filter

        elif previous_mode == 'range' and options_mode == 'single':
            # 'range' date mode to 'single'.

            if previous_filter == 'custom':
                date_to = fields.Date.from_string(previous_date_to or previous_date_from)
                date_from = date_utils.get_month(date_to)[0]
                options_filter = 'custom'
            elif previous_filter:
                options_filter = previous_filter
            else:
                options_filter = default_filter

        elif previous_mode == options_mode:
            # Same date mode.

            if previous_filter == 'custom':
                if options_mode == 'range':
                    date_from = fields.Date.from_string(previous_date_from)
                    date_to = fields.Date.from_string(previous_date_to)
                else:
                    date_to = fields.Date.from_string(previous_date_to or previous_date_from)
                    date_from = date_utils.get_month(date_to)[0]
                options_filter = 'custom'
            else:
                options_filter = previous_filter

        else:
            # Default.
            options_filter = default_filter

        # Compute 'date_from' / 'date_to'.
        if not date_from or not date_to:
            if options_filter == 'today':
                date_to = fields.Date.context_today(self)
                date_from = self.env.company.compute_fiscalyear_dates(date_to)['date_from']
                period_type = 'today'
            elif 'month' in options_filter:
                date_from, date_to = date_utils.get_month(fields.Date.context_today(self))
                period_type = 'month'
            elif 'quarter' in options_filter:
                date_from, date_to = date_utils.get_quarter(fields.Date.context_today(self))
                period_type = 'quarter'
            elif 'year' in options_filter:
                company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(fields.Date.context_today(self))
                date_from = company_fiscalyear_dates['date_from']
                date_to = company_fiscalyear_dates['date_to']
            elif options_filter == 'custom':
                custom_date_from = self.filter_date.get('date_from')
                custom_date_to = self.filter_date.get('date_to')
                date_to = fields.Date.from_string(custom_date_to or custom_date_from)
                date_from = fields.Date.from_string(custom_date_from) if custom_date_from else date_utils.get_month(date_to)[0]

        options['date'] = self._get_dates_period(
            date_from,
            date_to,
            options_mode,
            period_type=period_type,
        )
        if 'last' in options_filter:
            options['date'] = self._get_dates_previous_period(options, options['date'])
        options['date']['filter'] = options_filter

    def _init_options_comparison(self, options, previous_options=None):
        """ Initialize the 'comparison' options key.

        This filter must be loaded after the 'date' filter.

        :param options:             The current report options to build.
        :param previous_options:    The previous options coming from another report.
        """
        if not self.filter_period_comparison:
            return

        previous_comparison = (previous_options or {}).get('comparison', {})
        previous_filter = previous_comparison.get('filter')

        if previous_filter == 'custom':
            # Try to adapt the previous 'custom' filter.
            date_from = previous_comparison.get('date_from')
            date_to = previous_comparison.get('date_to')
            number_period = 1
            options_filter = 'custom'
        else:
            # Use the 'date' options.
            date_from = options['date']['date_from']
            date_to = options['date']['date_to']
            number_period = previous_comparison.get('number_period', 1)
            options_filter = previous_filter or 'no_comparison'

        options['comparison'] = {
            'filter': options_filter,
            'number_period': number_period,
            'date_from': date_from,
            'date_to': date_to,
            'periods': [],
        }

        date_from_obj = fields.Date.from_string(date_from)
        date_to_obj = fields.Date.from_string(date_to)

        if options_filter == 'custom':
            options['comparison']['periods'].append(self._get_dates_period(
                date_from_obj,
                date_to_obj,
                options['date']['mode'],
            ))
        elif options_filter in ('previous_period', 'same_last_year'):
            previous_period = options['date']
            for dummy in range(0, number_period):
                if options_filter == 'previous_period':
                    period_vals = self._get_dates_previous_period(options, previous_period)
                elif options_filter == 'same_last_year':
                    period_vals = self._get_dates_previous_year(options, previous_period)
                else:
                    date_from_obj = fields.Date.from_string(date_from)
                    date_to_obj = fields.Date.from_string(date_to)
                    period_vals = self._get_dates_period(date_from_obj, date_to_obj, previous_period['mode'])
                options['comparison']['periods'].append(period_vals)
                previous_period = period_vals

        if len(options['comparison']['periods']) > 0:
            options['comparison'].update(options['comparison']['periods'][0])

    def _init_options_growth_comparison(self, options, previous_options=None):
        options['show_growth_comparison'] = self._display_growth_comparison(options)

    def _get_options_date_domain(self, options, date_scope):
        date_from, date_to, allow_include_initial_balance = self._get_date_bounds_info(options, date_scope)

        scope_domain = [('date', '<=', date_to)]
        if date_from:
            if allow_include_initial_balance:
                scope_domain += [
                    '|',
                    ('date', '>=', date_from),
                    ('account_id.include_initial_balance', '=', True),
                ]
            else:
                scope_domain += [('date', '>=', date_from)]

        return scope_domain

    def _get_date_bounds_info(self, options, date_scope):
        # Default values (the ones from 'strict_range')
        date_to = options['date']['date_to']
        date_from = options['date']['date_from'] if options['date']['mode'] == 'range' else None
        allow_include_initial_balance = False

        if date_scope == 'normal':
            allow_include_initial_balance = True

        elif date_scope == 'from_beginning':
            date_from = None

        elif date_scope == 'to_beginning_of_period':
            date_tmp = fields.Date.from_string(date_from or date_to) - relativedelta(days=1)
            date_to = date_tmp.strftime('%Y-%m-%d')
            date_from = None

        elif date_scope == 'from_fiscalyear':
            date_tmp = fields.Date.from_string(date_to)
            date_tmp = self.env.company.compute_fiscalyear_dates(date_tmp)['date_from']
            date_from = date_tmp.strftime('%Y-%m-%d')

        elif date_scope == 'to_beginning_of_fiscalyear':
            date_tmp = fields.Date.from_string(date_to)
            date_tmp = self.env.company.compute_fiscalyear_dates(date_tmp)['date_from'] - relativedelta(days=1)
            date_to = date_tmp.strftime('%Y-%m-%d')
            date_from = None

        elif date_scope == 'previous_tax_period':
            eve_of_date_from = fields.Date.from_string(options['date']['date_from']) - relativedelta(days=1)
            date_from, date_to = self.env.company._get_tax_closing_period_boundaries(eve_of_date_from)

        return date_from, date_to, allow_include_initial_balance

    ####################################################
    # OPTIONS: analytic filter
    ####################################################

    def _init_options_analytic(self, options, previous_options=None):
        if not self.filter_analytic:
            return

        options['analytic'] = True  # Used in js, so we can't only rely on self.filter_analytic

        enable_analytic_accounts = self.user_has_groups('analytic.group_analytic_accounting')
        if not enable_analytic_accounts:
            return

        if enable_analytic_accounts:
            previous_analytic_accounts = (previous_options or {}).get('analytic_accounts', [])
            analytic_account_ids = [int(x) for x in previous_analytic_accounts]
            selected_analytic_accounts = self.env['account.analytic.account'].search([('id', 'in', analytic_account_ids)])
            options['analytic_accounts'] = selected_analytic_accounts.ids
            options['selected_analytic_account_names'] = selected_analytic_accounts.mapped('name')

    ####################################################
    # OPTIONS: partners
    ####################################################

    def _init_options_partner(self, options, previous_options=None):
        if not self.filter_partner:
            return

        options['partner'] = True
        options['partner_ids'] = previous_options and previous_options.get('partner_ids') or []
        options['partner_categories'] = previous_options and previous_options.get('partner_categories') or []
        selected_partner_ids = [int(partner) for partner in options['partner_ids']]
        selected_partners = selected_partner_ids and self.env['res.partner'].browse(selected_partner_ids) or self.env['res.partner']
        options['selected_partner_ids'] = selected_partners.mapped('name')
        selected_partner_category_ids = [int(category) for category in options['partner_categories']]
        selected_partner_categories = selected_partner_category_ids and self.env['res.partner.category'].browse(selected_partner_category_ids) or self.env['res.partner.category']
        options['selected_partner_categories'] = selected_partner_categories.mapped('name')

    @api.model
    def _get_options_partner_domain(self, options):
        domain = []
        if options.get('partner_ids'):
            partner_ids = [int(partner) for partner in options['partner_ids']]
            domain.append(('partner_id', 'in', partner_ids))
        if options.get('partner_categories'):
            partner_category_ids = [int(category) for category in options['partner_categories']]
            domain.append(('partner_id.category_id', 'in', partner_category_ids))
        return domain

    ####################################################
    # OPTIONS: all_entries
    ####################################################

    @api.model
    def _get_options_all_entries_domain(self, options):
        if not options.get('all_entries'):
            return [('parent_state', '=', 'posted')]
        else:
            return [('parent_state', '!=', 'cancel')]

    ####################################################
    # OPTIONS: not reconciled entries
    ####################################################
    def _init_options_reconciled(self, options, previous_options=None):
        if self.filter_unreconciled and previous_options:
            options['unreconciled'] = previous_options.get('unreconciled', False)
        else:
            options['unreconciled'] = False

    @api.model
    def _get_options_unreconciled_domain(self, options):
        if options.get('unreconciled'):
            return [('reconciled', '=', False)]
        return []

    ####################################################
    # OPTIONS: account_type
    ####################################################

    def _init_options_account_type(self, options, previous_options=None):
        '''
        Initialize a filter based on the account_type of the line (trade/non trade, payable/receivable).
        Selects a name to display according to the selections.
        The group display name is selected according to the display name of the options selected.
        '''
        if not self.filter_account_type:
            return

        options['account_type'] = [
            {'id': 'trade_receivable', 'name': _("Receivable"), 'selected': True},
            {'id': 'non_trade_receivable', 'name': _("Non Trade Receivable"), 'selected': False},
            {'id': 'trade_payable', 'name': _("Payable"), 'selected': True},
            {'id': 'non_trade_payable', 'name': _("Non Trade Payable"), 'selected': False},
        ]

        if previous_options and previous_options.get('account_type'):
            previously_selected_ids = {x['id'] for x in previous_options['account_type'] if x.get('selected')}
            for opt in options['account_type']:
                opt['selected'] = opt['id'] in previously_selected_ids

        selected_options = {x['id']: x['name'] for x in options['account_type'] if x['selected']}
        selected_ids = set(selected_options.keys())
        display_names = []

        def check_if_name_applicable(ids_to_match, string_if_match):
            '''
            If the ids selected are part of a possible grouping,
                - append the name of the grouping to display_names
                - Remove the concerned ids
            ids_to_match : the ids forming a group
            string_if_match : the group's name
            '''
            if len(selected_ids) == 0:
                return
            if ids_to_match.issubset(selected_ids):
                display_names.append(string_if_match)
                for selected_id in ids_to_match:
                    selected_ids.remove(selected_id)

        check_if_name_applicable({'trade_receivable', 'trade_payable', 'non_trade_receivable', 'non_trade_payable'}, _("All receivable/payable"))
        check_if_name_applicable({'trade_receivable', 'non_trade_receivable'}, _("All Receivable"))
        check_if_name_applicable({'trade_payable', 'non_trade_payable'}, _("All Payable"))
        check_if_name_applicable({'trade_receivable', 'trade_payable'}, _("Trade Partners"))
        check_if_name_applicable({'non_trade_receivable', 'non_trade_payable'}, _("Non Trade Partners"))
        for sel in selected_ids:
            display_names.append(selected_options.get(sel))
        options['account_display_name'] = ', '.join(display_names)

    @api.model
    def _get_options_account_type_domain(self, options):
        all_domains = []
        selected_domains = []
        if not options.get('account_type') or len(options.get('account_type')) == 0:
            return []
        for opt in options.get('account_type', []):
            if opt['id'] == 'trade_receivable':
                domain = [('account_id.non_trade', '=', False), ('account_id.account_type', '=', 'asset_receivable')]
            elif opt['id'] == 'trade_payable':
                domain = [('account_id.non_trade', '=', False), ('account_id.account_type', '=', 'liability_payable')]
            elif opt['id'] == 'non_trade_receivable':
                domain = [('account_id.non_trade', '=', True), ('account_id.account_type', '=', 'asset_receivable')]
            elif opt['id'] == 'non_trade_payable':
                domain = [('account_id.non_trade', '=', True), ('account_id.account_type', '=', 'liability_payable')]
            if opt['selected']:
                selected_domains.append(domain)
            all_domains.append(domain)
        return osv.expression.OR(selected_domains or all_domains)

    ####################################################
    # OPTIONS: order column
    ####################################################

    @api.model
    def _init_options_order_column(self, options, previous_options=None):
        # options['order_column'] is the index of a column (starting at 1, not 0), with + or - sign to represent the order in which we want to sort
        options['order_column'] = None

        previous_value = previous_options and previous_options.get('order_column')
        if previous_value:
            for index, col in enumerate(options['columns'], start=1):
                if col['sortable'] and index == abs(previous_value):
                    options['order_column'] = previous_value
                    break

    ####################################################
    # OPTIONS: hierarchy
    ####################################################

    def _init_options_hierarchy(self, options, previous_options=None):
        company_ids = self.get_report_company_ids(options)
        if self.filter_hierarchy != 'never' and self.env['account.group'].search([('company_id', 'in', company_ids)], limit=1):
            if previous_options and 'hierarchy' in previous_options:
                options['hierarchy'] = previous_options['hierarchy']
            else:
                options['hierarchy'] = self.filter_hierarchy == 'by_default'
        else:
            options['hierarchy'] = False

    @api.model
    def _create_hierarchy(self, lines, options):
        """Compute the hierarchy based on account groups when the option is activated.

        The option is available only when there are account.group for the company.
        It should be called when before returning the lines to the client/templater.
        The lines are the result of _get_lines(). If there is a hierarchy, it is left
        untouched, only the lines related to an account.account are put in a hierarchy
        according to the account.group's and their prefixes.
        """
        unfold_all = self.env.context.get('print_mode') and len(options.get('unfolded_lines')) == 0 or options.get('unfold_all')

        def get_account_group_hierarchy(account):
            # Create codes path in the hierarchy based on account.
            # A code is tuple(id, name)
            codes = []
            if account.group_id:
                group = account.group_id
                while group:
                    codes.append((group.id, group.display_name))
                    group = group.parent_id
            else:
                codes.append((0, _('(No Group)')))
            return list(reversed(codes))

        def add_to_hierarchy(lines, key, level, parent_id, hierarchy):
            val_dict = hierarchy[key]
            unfolded = val_dict['id'] in options.get('unfolded_lines') or unfold_all
            # add the group totals
            lines.append({
                'id': val_dict['id'],
                'name': val_dict['name'],
                'title_hover': val_dict['name'],
                'unfoldable': True,
                'unfolded': unfolded,
                'level': level,
                'parent_id': parent_id,
                'columns': [{
                    'name': self.format_value(c, figure_type='monetary') if isinstance(c, (int, float)) else c,
                    'no_format': c,
                    'class': 'number' if isinstance(c, (int, float)) else '',
                } for c in val_dict['totals']],
            })
            if not self._context.get('print_mode') or unfolded:
                for i in val_dict['children_codes']:
                    hierarchy[i]['parent_code'] = i
                all_lines = [hierarchy[id] for id in val_dict["children_codes"]] + val_dict["lines"]
                for line in sorted(all_lines, key=lambda k: k.get('account_code', '') + k['name']):
                    if 'children_codes' in line:
                        children = []
                        # if the line is a child group, add it recursively
                        add_to_hierarchy(children, line['parent_code'], level + 1, val_dict['id'], hierarchy)
                        lines.extend(children)
                    else:
                        # add lines that are in this group but not in one of this group's children groups
                        line['level'] = level + 1
                        line['parent_id'] = val_dict['id']
                        lines.append(line)

        def compute_hierarchy(lines, level, parent_id):
            # put every line in each of its parents (from less global to more global) and compute the totals
            hierarchy = defaultdict(lambda: {'totals': [None] * len(lines[0]['columns']), 'lines': [], 'children_codes': set(), 'name': '', 'parent_id': None, 'id': ''})
            for line in lines:
                res_model, model_id = self._get_model_info_from_id(line['id'])

                if res_model != 'account.account':
                    raise UserError(_("Trying to build account hierarchy from a model different from account.account: %s", res_model))

                account = self.env['account.account'].browse(model_id)
                account_groups = get_account_group_hierarchy(account)  # id, name
                for group_id, group_name in account_groups:
                    hierarchy[group_id]['id'] = self._get_generic_line_id('account.group', group_id, parent_line_id=line.get('parent_id'))
                    hierarchy[group_id]['name'] = group_name
                    for i, column in enumerate(line['columns']):
                        if 'no_format' in column:
                            no_format = column['no_format']
                        else:
                            no_format = None
                        if isinstance(no_format, (int, float)):
                            if hierarchy[group_id]['totals'][i] is None:
                                hierarchy[group_id]['totals'][i] = no_format
                            else:
                                hierarchy[group_id]['totals'][i] += no_format
                for (group_id, group_name), (child_group_id, dummy) in zip(account_groups[:-1], account_groups[1:]):
                    hierarchy[group_id]['children_codes'].add(child_group_id)
                    hierarchy[child_group_id]['parent_id'] = hierarchy[group_id]['id']
                    child_markup, child_model, child_id = self._parse_line_id(hierarchy[child_group_id]['id'])[-1]
                    hierarchy[child_group_id]['id'] = self._get_generic_line_id(child_model, child_id, markup=child_markup, parent_line_id=hierarchy[group_id]['id'])

                line_hierarchy_parent = hierarchy[account_groups[-1][0]]
                line['id'] = f"{line_hierarchy_parent['id']}|{line['id']}"
                line_hierarchy_parent['lines'].append(line)

            # compute the tree-like structure by starting at the roots (being groups without parents)
            hierarchy_lines = []
            for root in [k for k, v in hierarchy.items() if not v['parent_id']]:
                add_to_hierarchy(hierarchy_lines, root, level, parent_id, hierarchy)

            return hierarchy_lines

        new_lines = []
        account_lines = []
        current_level = 0
        parent_id = 'root'
        for line in lines:
            model = self._get_model_info_from_id(line['id'])[0]
            if model != 'account.account':
                # make the hierarchy with the lines we gathered, append it to the new lines and restart the gathering
                if account_lines:
                    new_lines.extend(compute_hierarchy(account_lines, current_level + 1, parent_id))
                account_lines = []
                new_lines.append(line)
                current_level = line['level']
                parent_id = line['id']
            else:
                # gather all the lines we can create a hierarchy on
                account_lines.append(line)
        # do it one last time for the gathered lines remaining
        if account_lines:
            new_lines.extend(compute_hierarchy(account_lines, current_level + 1, parent_id))
        return new_lines

    ####################################################
    # OPTIONS: fiscal position (multi vat)
    ####################################################

    def _init_options_fiscal_position(self, options, previous_options=None):
        if self.filter_fiscal_position and self.country_id and len(options.get('multi_company', [])) <= 1:
            vat_fpos_domain = [
                ('company_id', '=', next(comp_id for comp_id in self.get_report_company_ids(options))),
                ('foreign_vat', '!=', False),
            ]

            vat_fiscal_positions = self.env['account.fiscal.position'].search([
                *vat_fpos_domain,
                ('country_id', '=', self.country_id.id),
            ])

            options['allow_domestic'] = self.env.company.account_fiscal_country_id == self.country_id

            accepted_prev_vals = {*vat_fiscal_positions.ids}
            if options['allow_domestic']:
                accepted_prev_vals.add('domestic')
            if len(vat_fiscal_positions) > (0 if options['allow_domestic'] else 1) or not accepted_prev_vals:
                accepted_prev_vals.add('all')

            if previous_options and previous_options.get('fiscal_position') in accepted_prev_vals:
                # Legit value from previous options; keep it
                options['fiscal_position'] = previous_options['fiscal_position']
            elif len(vat_fiscal_positions) == 1 and not options['allow_domestic']:
                # Only one foreign fiscal position: always select it, menu will be hidden
                options['fiscal_position'] = vat_fiscal_positions.id
            else:
                # Multiple possible values; by default, show the values of the company's area (if allowed), or everything
                options['fiscal_position'] = options['allow_domestic'] and 'domestic' or 'all'
        else:
            # No country, or we're displaying data from several companies: disable fiscal position filtering
            vat_fiscal_positions = []
            options['allow_domestic'] = True
            previous_fpos = previous_options and previous_options.get('fiscal_position')
            options['fiscal_position'] = previous_fpos if previous_fpos in ('all', 'domestic') else 'all'

        options['available_vat_fiscal_positions'] = [{
            'id': fiscal_pos.id,
            'name': fiscal_pos.name,
            'company_id': fiscal_pos.company_id.id,
        } for fiscal_pos in vat_fiscal_positions]

    def _get_options_fiscal_position_domain(self, options):
        fiscal_position_opt = options.get('fiscal_position')

        if fiscal_position_opt == 'domestic':
            return [
                '|',
                ('move_id.fiscal_position_id', '=', False),
                ('move_id.fiscal_position_id.foreign_vat', '=', False),
            ]

        if isinstance(fiscal_position_opt, int):
            # It's a fiscal position id
            return [('move_id.fiscal_position_id', '=', fiscal_position_opt)]

        # 'all', or option isn't specified
        return []

    ####################################################
    # OPTIONS: MULTI COMPANY
    ####################################################

    def _init_options_multi_company(self, options, previous_options=None):
        if self.filter_multi_company == 'selector':
            self._multi_company_selector_init_options(options, previous_options=previous_options)
        elif self.filter_multi_company == 'tax_units':
            self._multi_company_tax_units_init_options(options, previous_options=previous_options)

    def _multi_company_selector_init_options(self, options, previous_options=None):
        """ Initializes the multi_company option for reports configured to compute it from the company selector.
        """
        if len(self.env.companies) > 1:
            options['multi_company'] = [
                {'id': c.id, 'name': c.name} for c in self.env.companies
            ]

    def _multi_company_tax_units_init_options(self, options, previous_options=None):
        """ Initializes the multi_company option for reports configured to compute it from tax units.
        """
        tax_units_domain = [('company_ids', 'in', self.env.company.id)]

        if self.country_id:
            tax_units_domain.append(('country_id', '=', self.country_id.id))

        available_tax_units = self.env['account.tax.unit'].search(tax_units_domain)

        # Filter available units to only consider the ones whose companies are all accessible to the user
        available_tax_units = available_tax_units.filtered(
            lambda x: all(unit_company in self.env.user.company_ids for unit_company in x.sudo().company_ids)
            # sudo() to avoid bypassing companies the current user does not have access to
        )

        options['available_tax_units'] = [{
            'id': tax_unit.id,
            'name': tax_unit.name,
            'company_ids': tax_unit.company_ids.ids
        } for tax_unit in available_tax_units]

        # Available tax_unit option values that are currently allowed by the company selector
        # A js hack ensures the page is reloaded and the selected companies modified
        # when clicking on a tax unit option in the UI, so we don't need to worry about that here.
        companies_authorized_tax_unit_opt = {
            *(available_tax_units.filtered(lambda x: set(self.env.companies) == set(x.company_ids)).ids),
            'company_only'
        }

        if previous_options and previous_options.get('tax_unit') in companies_authorized_tax_unit_opt:
            options['tax_unit'] = previous_options['tax_unit']

        else:
            # No tax_unit gotten from previous options; initialize it
            # A tax_unit will be set by default if only one tax unit is available for the report
            # (which should always be true for non-generic reports, which have a country), and the companies of
            # the unit are the only ones currently selected.
            if companies_authorized_tax_unit_opt == {'company_only'}:
                options['tax_unit'] = 'company_only'
            elif len(available_tax_units) == 1 and available_tax_units[0].id in companies_authorized_tax_unit_opt:
                options['tax_unit'] = available_tax_units[0].id
            else:
                options['tax_unit'] = 'company_only'

        # Finally initialize multi_company filter
        if options['tax_unit'] != 'company_only':
            tax_unit = available_tax_units.filtered(lambda x: x.id == options['tax_unit'])
            options['multi_company'] = [{'name': company.name, 'id': company.id} for company in tax_unit.company_ids]

    ####################################################
    # OPTIONS: ALL ENTRIES
    ####################################################
    def _init_options_all_entries(self, options, previous_options=None):
        if self.filter_show_draft and previous_options:
            options['all_entries'] = previous_options.get('all_entries', False)
        else:
            options['all_entries'] = False

    ####################################################
    # OPTIONS: UNFOLD ALL
    ####################################################
    def _init_options_unfold_all(self, options, previous_options=None):
        if self.filter_unfold_all and previous_options:
            options['unfold_all'] = (previous_options or {}).get('unfold_all', False)
        else:
            options['unfold_all'] = False # Disables the filter in the UI

    ####################################################
    # OPTIONS: HORIZONTAL GROUP
    ####################################################
    def _init_options_horizontal_groups(self, options, previous_options=None):
        options['available_horizontal_groups'] = [
            {
                'id': horizontal_group.id,
                'name': horizontal_group.name,
            }
            for horizontal_group in self.horizontal_group_ids
        ]
        previous_selected = (previous_options or {}).get('selected_horizontal_group_id')
        options['selected_horizontal_group_id'] = previous_selected if previous_selected in self.horizontal_group_ids.ids else None

    ####################################################
    # OPTIONS: SEARCH BAR
    ####################################################
    def _init_options_search_bar(self, options, previous_options=None):
        if self.search_bar:
            options['search_bar'] = True

    ####################################################
    # OPTIONS: COLUMNS
    ####################################################
    def _init_options_columns(self, options, previous_options=None):
        self._set_column_headers(options)
        default_group_vals = {'horizontal_groupby_element': {}, 'forced_options': {}}
        all_column_group_vals_in_order = self._generate_columns_group_vals_recursively(options['column_headers'], default_group_vals)

        columns, column_groups = self._build_columns_from_column_group_vals(options, all_column_group_vals_in_order)

        options['columns'] = columns
        options['column_groups'] = column_groups
        # Debug column is only shown when there is a single column group, so that we can display all the subtotals of the line in a clear way
        options['show_debug_column'] = not self._context.get('print_mode') \
                                       and self.user_has_groups('base.group_no_one') \
                                       and len(options['column_groups']) == 1 \
                                       and len(self.line_ids) > 0 # No debug column on fully dynamic reports by default (they can customize this)

    def _generate_columns_group_vals_recursively(self, next_levels_headers, previous_levels_group_vals):
        if next_levels_headers:
            rslt = []
            for header_element in next_levels_headers[0]:
                current_level_group_vals = {}
                for key in previous_levels_group_vals:
                    current_level_group_vals[key] = {**previous_levels_group_vals.get(key, {}), **header_element.get(key, {})}

                rslt += self._generate_columns_group_vals_recursively(next_levels_headers[1:], current_level_group_vals)
            return rslt
        else:
            return [previous_levels_group_vals]

    def _build_columns_from_column_group_vals(self, options, all_column_group_vals_in_order):
        def _generate_domain_from_horizontal_group_hash_key_tuple(group_hash_key):
            domain = []
            for field_name, field_value in group_hash_key:
                domain.append((field_name, '=', field_value))
            return domain

        columns = []
        column_groups = {}
        for column_group_val in all_column_group_vals_in_order:
            horizontal_group_key_tuple = self._get_dict_hashable_key_tuple(column_group_val['horizontal_groupby_element']) # Empty tuple if no grouping
            column_group_key = str(self._get_dict_hashable_key_tuple(column_group_val)) # Unique identifier for the column group

            column_groups[column_group_key] = {
                'forced_options': column_group_val['forced_options'],
                'forced_domain': _generate_domain_from_horizontal_group_hash_key_tuple(horizontal_group_key_tuple),
            }

            for report_column in self.column_ids:
                columns.append({
                    'name': report_column.name,
                    'column_group_key': column_group_key,
                    'expression_label': report_column.expression_label,
                    'sortable': report_column.sortable,
                    'figure_type': report_column.figure_type,
                    'blank_if_zero': report_column.blank_if_zero,
                    'style': "text-align: center; white-space: nowrap;",
                })

        return columns, column_groups

    def _set_column_headers(self, options):
        # Prepare column headers
        all_comparison_date_vals = [options['date']] + options.get('comparison', {}).get('periods', [])
        column_headers = [
            [
                {
                    'name': comparison_date_vals['string'],
                    'forced_options': {'date': comparison_date_vals},
                }
                for comparison_date_vals in all_comparison_date_vals
            ], # First level always consists of date comparison. Horizontal groupby are done on following levels.
        ]

        # Handle horizontal groups
        selected_horizontal_group_id = options.get('selected_horizontal_group_id')
        if selected_horizontal_group_id:
            horizontal_group = self.env['account.report.horizontal.group'].browse(selected_horizontal_group_id)

            for field_name, records in horizontal_group._get_header_levels_data():
                header_level = [
                    {
                        'name': record.display_name,
                        'horizontal_groupby_element': {field_name: record.id},
                    }
                    for record in records
                ]
                column_headers.append(header_level)

        options['column_headers'] = column_headers

    def _get_dict_hashable_key_tuple(self, dict_to_convert):
        rslt = []
        for key, value in sorted(dict_to_convert.items()):
            if isinstance(value, dict):
                value = self._get_dict_hashable_key_tuple(value)
            rslt.append((key, value))
        return tuple(rslt)

    ####################################################
    # OPTIONS: BUTTONS
    ####################################################
    def _init_options_buttons(self, options, previous_options=None):
        options['buttons'] = [
            {'name': _('PDF'), 'sequence': 10, 'action': 'export_file', 'action_param': 'export_to_pdf', 'file_export_type': _('PDF')},
            {'name': _('XLSX'), 'sequence': 20, 'action': 'export_file', 'action_param': 'export_to_xlsx', 'file_export_type': _('XLSX')},
            {'name': _('Save'), 'sequence': 100, 'action': 'open_report_export_wizard'},
        ]

    def open_report_export_wizard(self, options):
        """ Creates a new export wizard for this report and returns an act_window
        opening it. A new account_report_generation_options key is also added to
        the context, containing the current options selected on this report
        (which must hence be taken into account when exporting it to a file).
        """
        self.ensure_one()
        new_context = {
            **self._context,
            'account_report_generation_options': options,
            'default_report_id': self.id,
        }
        view_id = self.env.ref('account_reports.view_report_export_wizard').id

        # We have to create it before returning the action (and not just use a record in 'new' state), so that we can create
        # the transient records used in the m2m for the different export formats.
        new_wizard = self.with_context(new_context).env['account_reports.export.wizard'].create({'report_id': self.id})

        return {
            'type': 'ir.actions.act_window',
            'name': _('Export'),
            'view_mode': 'form',
            'res_model': 'account_reports.export.wizard',
            'res_id': new_wizard.id,
            'target': 'new',
            'views': [[view_id, 'form']],
            'context': new_context,
        }

    def get_export_mime_type(self, file_type):
        """ Returns the MIME type associated with a report export file type,
        for attachment generation.
        """
        type_mapping = {
            'xlsx': 'application/vnd.ms-excel',
            'pdf': 'application/pdf',
            'xml': 'application/xml',
            'xaf': 'application/vnd.sun.xml.writer',
            'txt': 'text/plain',
            'csv': 'text/csv',
            'zip': 'application/zip',
        }
        return type_mapping.get(file_type, False)

    ####################################################
    # OPTIONS: VARIANTS
    ####################################################
    def _init_options_variants(self, options, previous_options=None):
        available_variants = []
        allowed_variant_ids = set()
        allowed_country_variant_ids = {}
        for variant in self._get_variants().filtered(lambda x: x._is_available_for(options)):
            if not self.root_report_id and variant != self:
                allowed_variant_ids.add(variant.id)
                if variant.country_id:
                    allowed_country_variant_ids.setdefault(variant.country_id.id, []).append(variant.id)

            available_variants.append({
                'id': variant.id,
                'name': variant.display_name,
                'country_id': variant.country_id.id,  # To ease selection of default variant to open, without needing browsing again
            })

        options['available_variants'] = list(sorted(available_variants, key=lambda x: x['country_id'] and 1 or 0))

        previous_opt_report_id = (previous_options or {}).get('report_id')
        if previous_opt_report_id in allowed_variant_ids or previous_opt_report_id == self.id:
            options['report_id'] = previous_opt_report_id
        elif allowed_country_variant_ids:
            country_id = self.env.company.account_fiscal_country_id.id
            report_id = (allowed_country_variant_ids.get(country_id) or next(iter(allowed_country_variant_ids.values())))[0]
            options['report_id'] = report_id
        else:
            options['report_id'] = self.id

    ####################################################
    # OPTIONS: CUSTOM
    ####################################################
    def _init_options_custom(self, options, previous_options=None):
        if self.custom_handler_model_id:
            self.env[self.custom_handler_model_name]._custom_options_initializer(self, options, previous_options)

    ####################################################
    # OPTIONS: CORE
    ####################################################

    def _get_options(self, previous_options=None):
        self.ensure_one()
        # Create default options.
        options = {'unfolded_lines': (previous_options or {}).get('unfolded_lines', [])}

        for initializer in self._get_options_initializers_in_sequence():
            initializer(options, previous_options=previous_options)

        # Sort the buttons list by sequence, for rendering
        options['buttons'] = sorted(options['buttons'], key=lambda x: x.get('sequence', 90))

        return options

    def _get_variants(self):
        self.ensure_one()
        root_report = self.root_report_id if self.root_report_id else self
        return root_report + root_report.variant_report_ids

    def _get_options_initializers_in_sequence(self):
        """ Gets all filters in the right order to initialize them, so that each filter is
        guaranteed to be after all of its dependencies in the resulting list.

        :return: a list of initializer functions, each accepting two parameters:
            - options (mandatory): The options dictionary to be modified by this initializer to include its related option's data

            - previous_options (optional, defaults to None): A dict with default options values, coming from a previous call to the report.
                                                             These values can be considered or ignored on a case-by-case basis by the initializer,
                                                             depending on functional needs.
        """
        initializer_prefix = '_init_options_'
        initializers = [
            getattr(self, attr) for attr in dir(self)
            if attr.startswith(initializer_prefix)
        ]

        # Order them in a dependency-compliant way
        forced_sequence_map = self._get_options_initializers_forced_sequence_map()
        initializers.sort(key=lambda x: forced_sequence_map.get(x, forced_sequence_map.get('default')))

        return initializers

    def _get_options_initializers_forced_sequence_map(self):
        """ By default, not specific order is ensured for the filters when calling _get_options_initializers_in_sequence.
        This function allows giving them a sequence number. It can be overridden
        to make filters depend on each other.

        :return: dict(str, int): str is the filter name, int is its sequence (lowest = first).
                                 Multiple filters may share the same sequence, their relative order is then not guaranteed.
        """
        return {
            self._init_options_multi_company: 10,
            self._init_options_variants: 15,
            self._init_options_fiscal_position: 20,
            self._init_options_date: 30,
            self._init_options_horizontal_groups: 40,
            self._init_options_comparison: 50,

            'default': 200,

            self._init_options_columns: 1000,
            self._init_options_growth_comparison: 1010,
            self._init_options_order_column: 1020,
            self._init_options_hierarchy: 1030,
            self._init_options_custom: 1050,
        }

    def _get_options_domain(self, options, date_scope):
        self.ensure_one()

        available_scopes = dict(self.env['account.report.expression']._fields['date_scope'].selection)
        if date_scope not in available_scopes:
            raise UserError(_("Unknown date scope: %s", date_scope))

        domain = [
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('parent_state', '!=', 'cancel'),
            ('company_id', 'in', self.get_report_company_ids(options)),
        ]
        domain += self._get_options_journals_domain(options)
        domain += self._get_options_date_domain(options, date_scope)
        domain += self._get_options_partner_domain(options)
        domain += self._get_options_all_entries_domain(options)
        domain += self._get_options_unreconciled_domain(options)
        domain += self._get_options_fiscal_position_domain(options)
        domain += self._get_options_account_type_domain(options)

        if self.only_tax_exigible:
            domain += self.env['account.move.line']._get_tax_exigible_domain()

        return domain

    ####################################################
    # QUERIES
    ####################################################

    @api.model
    def _query_get(self, options, date_scope, domain=None):
        domain = self._get_options_domain(options, date_scope) + (domain or [])

        if options.get('forced_domain'):
            # That option key is set when splitting options between column groups
            domain += options['forced_domain']

        self.env['account.move.line'].check_access_rights('read')

        query = self.env['account.move.line']._where_calc(domain)

        # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
        self.env['account.move.line']._apply_ir_rules(query)

        return query.get_sql()

    ####################################################
    # LINE IDS MANAGEMENT HELPERS
    ####################################################
    @api.model
    def _get_generic_line_id(self, model_name, value, markup='', parent_line_id=None):
        """ Generates a generic line id from the provided parameters.

        Such a generic id consists of a string repeating 1 to n times the following pattern:
        markup-model-value, each occurence separated by a | character from the previous one.

        Each pattern corresponds to a level of hierarchy in the report, so that
        the n-1 patterns starting the id of a line actually form the id of its generator line.
        EX: a-b-c|d-e-f|g-h-i => This line is a subline generated by a-b-c|d-e-f

        Each pattern consists of the three following elements:
        - markup:  a (possibly empty) string allowing finer identification of the line
                   (like the name of the field for account.accounting.reports)

        - model:   the model this line has been generated for, or an empty string if there is none

        - value:   the groupby value for this line (typically the id of a record
                   or the value of a field), or an empty string if there isn't any.
        """
        parent_id_list = self._parse_line_id(parent_line_id) if parent_line_id else []
        return self._build_line_id(parent_id_list + [(markup, model_name, value)])

    @api.model
    def _get_model_info_from_id(self, line_id):
        """ Parse the provided generic report line id.

        :param line_id: the report line id (i.e. markup-model-value|markup2-model2-value2)
        :return: tuple(model, id) of the report line. Each of those values can be None if the id contains no information about them.
        """
        last_id_tuple = self._parse_line_id(line_id)[-1]
        return last_id_tuple[-2:]

    @api.model
    def _build_line_id(self, current):
        """ Build a generic line id string from its list representation, converting
        the None values for model and value to empty strings.
        :param current (list<tuple>): list of tuple(markup, model, value)
        """
        def convert_none(x):
            return x if x not in (None, False) else ''
        return '|'.join(f'{convert_none(markup)}-{convert_none(model)}-{convert_none(value)}' for markup, model, value in current)

    @api.model
    def _build_parent_line_id(self, current):
        """Build the parent_line id based on the current position in the report.

        For instance, if current is [(account_id, 5), (partner_id, 8)], it will return
        account_id-5
        :param current (list<tuple>): list of tuple(markup, model, value)
        """
        return self._build_line_id(current[:-1])

    @api.model
    def _parse_line_id(self, line_id):
        """Parse the provided string line id and convert it to its list representation.
        Empty strings for model and value will be converted to None.

        For instance if line_id is markup1-account_id-5|markup2-partner_id-8, it will return
        [(markup1, account_id, 5), (markup2, partner_id, 8)]
        :param line_id (str): the generic line id to parse
        """
        return line_id and [
            # 'value' can sometimes be a string percentage, i.e. "20.0".
            # To prevent a ValueError, we need to convert it into a float first, then into an int.
            (markup, model or None, int(float(value)) if value else None)
            for markup, model, value in (key.split('-') for key in line_id.split('|'))
        ] or []

    @api.model
    def _get_unfolded_lines(self, lines, parent_line_id):
        """ Return a list of all children lines for specified parent_line_id.
        NB: It will return the parent_line itself!

        For instance if parent_line_ids is '-account.report.line-84|groupby:currency_id-res.currency-174',
        it will return every subline for this currency.
        :param lines: list of report lines
        :param parent_line_id: id of a specified line
        :return: A list of all children lines for a specified parent_line_id
        """
        return [
            line for line in lines
            if line['id'].startswith(parent_line_id)
        ]

    ####################################################
    # CARET OPTIONS MANAGEMENT
    ####################################################

    def _get_caret_options(self):
        if self.custom_handler_model_id:
            return self.env[self.custom_handler_model_name]._caret_options_initializer()
        return self._caret_options_initializer_default()

    def _caret_options_initializer_default(self):
        return {
            'account.account': [
                {'name': _("General Ledger"), 'action': 'caret_option_open_general_ledger'},
            ],

            'account.move': [
                {'name': _("View Journal Entry"), 'action': 'caret_option_open_record_form'},
            ],

            'account.move.line': [
                {'name': _("View Journal Entry"), 'action': 'caret_option_open_record_form', 'action_param': 'move_id'},
            ],

            'account.payment': [
                {'name': _("View Payment"), 'action': 'caret_option_open_record_form', 'action_param': 'payment_id'},
            ],

            'account.bank.statement': [
                {'name': _("View Bank Statement"), 'action': 'caret_option_open_statement_line_reco_widget'},
            ],

            'res.partner': [
                {'name': _("View Partner"), 'action': 'caret_option_open_record_form'},
            ],
        }

    def caret_option_open_record_form(self, options, params):
        model, record_id = self._get_model_info_from_id(params['line_id'])
        record = self.env[model].browse(record_id)
        target_record = record[params['action_param']] if 'action_param' in params else record

        view_id = self._resolve_caret_option_view(target_record)

        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(view_id, 'form')], # view_id will be False in case the default view is needed
            'res_model': target_record._name,
            'res_id': target_record.id,
            'context': self._context,
        }

        if view_id is not None:
            action['view_id'] = view_id

        return action

    def _get_caret_option_view_map(self):
        return {
            'account.payment': 'account.view_account_payment_form',
            'res.partner': 'base.view_partner_form',
            'account.move': 'account.view_move_form',
        }

    def _resolve_caret_option_view(self, target):
        '''Retrieve the target view of the caret option.

        :param target:  The target record of the redirection.
        :return: The id of the target view.
        '''
        view_map = self._get_caret_option_view_map()

        view_xmlid = view_map.get(target._name)
        if not view_xmlid:
            return None

        return self.env['ir.model.data']._xmlid_lookup(view_xmlid)[2]

    def caret_option_open_general_ledger(self, options, params):
        model, record_id = self._get_model_info_from_id(params['line_id'])

        if model != 'account.account':
            raise UserError(_("'Open General Ledger' caret option is only available form report lines targetting accounts."))

        account_line_id = self._get_generic_line_id('account.account', record_id)
        gl_options = self.env.ref('account_reports.general_ledger_report')._get_options(options)
        gl_options['unfolded_lines'] = [account_line_id]

        action_vals = self.env['ir.actions.actions']._for_xml_id('account_reports.action_account_report_general_ledger')
        action_vals['params'] = {
            'options': gl_options,
            'ignore_session': 'read',
        }

        return action_vals

    def caret_option_open_statement_line_reco_widget(self, options, params):
        model, record_id = self._get_model_info_from_id(params['line_id'])
        record = self.env[model].browse(record_id)
        if record._name == 'account.bank.statement.line':
            return record.action_open_recon_st_line()
        elif record._name == 'account.bank.statement':
            return record.action_open_bank_reconcile_widget()
        raise UserError(_("'View Bank Statement' caret option is only available for report lines targeting bank statements."))

    ####################################################
    # MISC
    ####################################################
    def dispatch_report_action(self, options, action, action_param=None):
        """ Dispatches calls made by the client to either the report itself, or its custom handler if it exists.
            The action should be a public method, by definition, but a check is made to make sure
            it is not trying to call a private method.
        """
        self.ensure_one()
        check_method_name(action)
        args = [options, action_param] if action_param is not None else [options]
        if self.custom_handler_model_id:
            handler = self.env[self.custom_handler_model_name]
            if hasattr(handler, action):
                return getattr(handler, action)(*args)
        return getattr(self, action)(*args)

    def _get_custom_report_function(self, function_name, prefix):
        """ Returns a report function from its name, first checking it to ensure it's private (and raising if it isn't).
            This helper is used by custom report fields containing function names.
            The function will be called on the report's custom handler if it exists, or on the report itself otherwise.
        """
        self.ensure_one()
        function_name_prefix = f'_report_{prefix}_'
        if not function_name.startswith(function_name_prefix):
            raise UserError(_("Method '%s' must start with the '%s' prefix.", function_name, function_name_prefix))

        if self.custom_handler_model_id:
            handler = self.env[self.custom_handler_model_name]
            if hasattr(handler, function_name):
                return getattr(handler, function_name)

        # Call the check method without the private prefix to check for others security risks.
        return getattr(self, function_name)

    def _get_lines(self, options, all_column_groups_expression_totals=None):
        self.ensure_one()

        if options['report_id'] != self.id:
            # Should never happen; just there to prevent BIG issues and directly spot them
            raise UserError(_("Inconsistent report_id in options dictionary. Options says %s; report is %s.", options['report_id'], self.id))

        # Necessary to ensure consistency of the data if some of them haven't been written in database yet
        self.env.flush_all()

        # Merge static and dynamic lines in a common list
        if all_column_groups_expression_totals is None:
            all_column_groups_expression_totals = self._compute_expression_totals_for_each_column_group(self.line_ids.expression_ids, options)

        dynamic_lines = self._get_dynamic_lines(options, all_column_groups_expression_totals)

        lines = []
        line_cache = {} # {report_line: report line dict}
        hide_if_zero_lines = self.env['account.report.line']

        # There are two types of lines:
        # - static lines: the ones generated from self.line_ids
        # - dynamic lines: the ones generated from a call to the functions referred to by self.dynamic_lines_generator
        # This loops combines both types of lines together within the lines list
        for line in self.line_ids: # _order ensures the sequence of the lines
            # Inject all the dynamic lines whose sequence is inferior to the next static line to add
            while dynamic_lines and line.sequence > dynamic_lines[0][0]:
                lines.append(dynamic_lines.pop(0)[1])

            parent_generic_id = line_cache[line.parent_id]['id'] if line.parent_id else None # The parent line has necessarily been treated in a previous iteration
            line_dict = self._get_static_line_dict(options, line, all_column_groups_expression_totals, parent_id=parent_generic_id)
            line_cache[line] = line_dict

            if line.hide_if_zero:
                hide_if_zero_lines += line

            lines.append(line_dict)

        for dummy, left_dynamic_line in dynamic_lines:
            lines.append(left_dynamic_line)

        # Manage hide_if_zero lines:
        # - If they have column values: hide them if all those values are 0 (or empty)
        # - If they don't: hide them if all their children's column values are 0 (or empty)
        # Also, hide all the children of a hidden line.
        hidden_lines_dict_ids = set()
        for line in hide_if_zero_lines:
            children_to_check = line
            current = line
            while current:
                children_to_check |= current
                current = current.children_ids

            all_children_zero = True
            hide_candidates = set()
            for child in children_to_check:
                child_line_dict_id = line_cache[child]['id']

                if child_line_dict_id in hidden_lines_dict_ids:
                    continue
                elif all(col.get('is_zero', True) for col in line_cache[child]['columns']):
                    hide_candidates.add(child_line_dict_id)
                else:
                    all_children_zero = False
                    break

            if all_children_zero:
                hidden_lines_dict_ids |= hide_candidates

        lines[:] = filter(lambda x: x['id'] not in hidden_lines_dict_ids and x.get('parent_id') not in hidden_lines_dict_ids, lines)

        # Create the hierarchy of lines if necessary
        if options.get('hierarchy'):
            lines = self._create_hierarchy(lines, options)

        # Unfold lines (static or dynamic) if necessary and prepare totals below section
        lines = self._fully_unfold_lines_if_needed(lines, options)

        # Handle totals below sections setting
        if self.env.company.totals_below_sections and not options.get('ignore_totals_below_sections'):

            # Gather the lines needing the totals
            lines_needing_total_below = set()
            for line_dict, child_dict in zip(lines, lines[1:] + [None]):
                line_markup = self._parse_line_id(line_dict['id'])[-1][0]

                if line_markup != 'total':
                    # If we are on the first level of a groupby, wee need to add the total below section now.
                    # Sublevels (if any) will be handled by _expand_groupby.
                    has_child = child_dict and child_dict.get('parent_id') == line_dict['id']
                    if (line_dict.get('unfoldable') or has_child) and not line_markup.startswith('groupby'):
                        lines_needing_total_below.add(line_dict['id'])

                    # All lines that are parent of other lines need to receive a total if thery're not a groupby themselves
                    line_parent_id = line_dict.get('parent_id')
                    if line_parent_id and not line_markup.startswith('groupby'):
                        lines_needing_total_below.add(line_parent_id)

            # Inject the totals
            if lines_needing_total_below:
                lines_with_totals_below = []
                totals_below_stack = []
                for line_dict in lines:
                    while totals_below_stack and not line_dict['id'].startswith(totals_below_stack[-1]['parent_id']):
                        lines_with_totals_below.append(totals_below_stack.pop())

                    lines_with_totals_below.append(line_dict)

                    if line_dict['id'] in lines_needing_total_below and any(col.get('no_format') is not None for col in line_dict['columns']):
                        line_dict['class'] = f"{line_dict.get('class', '')} o_account_reports_totals_below_sections"
                        totals_below_stack.append(self._generate_total_below_section_line(line_dict))

                while totals_below_stack:
                    lines_with_totals_below.append(totals_below_stack.pop())

                lines = lines_with_totals_below

        if self.custom_handler_model_id:
            lines = self.env[self.custom_handler_model_name]._custom_line_postprocessor(self, options, lines)

        return lines

    def _fully_unfold_lines_if_needed(self, lines, options):
        def line_need_expansion(line_dict):
            return line_dict.get('unfolded') and line_dict.get('expand_function')

        custom_unfold_all_batch_data = None

        # If it's possible to batch unfold and we're unfolding all lines, compute the batch, so that individual expansions are more efficient
        if (self._context.get('print_mode') or options.get('unfold_all')) and self.custom_handler_model_id:
            lines_to_expand_by_function = {}
            for line_dict in lines:
                if line_need_expansion(line_dict):
                    lines_to_expand_by_function.setdefault(line_dict['expand_function'], []).append(line_dict)

            custom_unfold_all_batch_data = self.env[self.custom_handler_model_name]._custom_unfold_all_batch_data_generator(self, options, lines_to_expand_by_function)

        i = 0
        while i < len(lines):
            # We iterate in such a way that if the lines added by an expansion need expansion, they will get it as well
            line_dict = lines[i]
            if line_need_expansion(line_dict):
                groupby = line_dict.get('groupby')
                progress = line_dict.get('progress')
                to_insert = self._expand_unfoldable_line(line_dict['expand_function'], line_dict['id'], groupby, options, progress, 0,
                                                         unfold_all_batch_data=custom_unfold_all_batch_data)
                lines = lines[:i+1] + to_insert + lines[i+1:]
            i += 1

        return lines

    def _generate_total_below_section_line(self, section_line_dict):
        return {
            **section_line_dict,
            'id': self._get_generic_line_id(None, None, parent_line_id=section_line_dict['id'], markup='total'),
            'level': section_line_dict['level'] + 1,
            'class': 'total',
            'name': _("Total %s", section_line_dict['name']),
            'parent_id': section_line_dict['id'],
            'unfoldable': False,
            'unfolded': False,
            'caret_options': None,
            'action_id': None,
        }

    def _get_static_line_dict(self, options, line, all_column_groups_expression_totals, parent_id=None):
        line_id = self._get_generic_line_id('account.report.line', line.id, parent_line_id=parent_id)
        columns = self._build_static_line_columns(line, options, all_column_groups_expression_totals)

        rslt = {
            'id': line_id,
            'name': line.name,
            'groupby': line.groupby,
            'unfoldable': line.foldable and (any(col['has_sublines'] for col in columns) or bool(line.children_ids)),
            'unfolded': bool((not line.foldable and (line.children_ids or line.groupby)) or line_id in options.get('unfolded_lines', {})) or options.get('unfold_all'),
            'columns': columns,
            'level': line.hierarchy_level,
            'page_break': line.print_on_new_page,
            'action_id': line.action_id.id,
            'expand_function': line.groupby and '_report_expand_unfoldable_line_with_groupby' or None,
        }

        if parent_id:
            rslt['parent_id'] = parent_id

        if options['show_debug_column']:
            first_group_key = list(options['column_groups'].keys())[0]
            column_group_totals = all_column_groups_expression_totals[first_group_key]
            # Only consider the first column group, as show_debug_column is only true if there is but one.

            engine_selection_labels = dict(self.env['account.report.expression']._fields['engine']._description_selection(self.env))
            expressions_detail = defaultdict(lambda: [])
            col_expression_to_figure_type = {
                column.get('expression_label'): column.get('figure_type') for column in options['columns']
            }
            for expression in line.expression_ids:
                engine_label = engine_selection_labels[expression.engine]
                figure_type = expression.figure_type or col_expression_to_figure_type.get(expression.label) or 'none'
                expressions_detail[engine_label].append((
                    expression.label,
                    {'formula': expression.formula, 'subformula': expression.subformula, 'value': self.format_value(column_group_totals[expression]['value'], figure_type=figure_type, blank_if_zero=False)}
                ))

            # Sort results so that they can be rendered nicely in the UI
            for details in expressions_detail.values():
                details.sort(key=lambda x: x[0])
            sorted_expressions_detail = sorted(expressions_detail.items(), key=lambda x: x[0])

            rslt['debug_popup_data'] = json.dumps({'expressions_detail': sorted_expressions_detail})

        # Growth comparison column.
        if self._display_growth_comparison(options):
            compared_expression = line.expression_ids.filtered(lambda expr: expr.label == rslt['columns'][0]['expression_label'])
            first_value = columns[0]['no_format']
            second_value = columns[1]['no_format']
            if not first_value and not second_value:  # For layout lines and such, with no values
                rslt['growth_comparison_data'] = {'name': '', 'class': ''}
            else:
                rslt['growth_comparison_data'] = self._compute_growth_comparison_column(
                    options, first_value, second_value, green_on_positive=compared_expression.green_on_positive)

        return rslt

    @api.model
    def _build_static_line_columns(self, line, options, all_column_groups_expression_totals):
        line_expressions_map = {expr.label: expr for expr in line.expression_ids}
        columns = []
        for column_data in options['columns']:
            current_group_expression_totals = all_column_groups_expression_totals[column_data['column_group_key']]
            target_line_res_dict = {expr.label: current_group_expression_totals[expr] for expr in line.expression_ids}

            column_expr_label = column_data['expression_label']
            column_res_dict = target_line_res_dict.get(column_expr_label, {})
            column_value = column_res_dict.get('value')
            column_has_sublines = column_res_dict.get('has_sublines', False)
            column_expression = line_expressions_map.get(column_expr_label, self.env['account.report.expression'])
            figure_type = column_expression.figure_type or column_data['figure_type']

            # Handle info popup
            info_popup_data = {}

            # Check carryover
            carryover_expr_label = '_carryover_%s' % column_expr_label
            carryover_value = target_line_res_dict.get(carryover_expr_label, {}).get('value', 0)
            if self.env.company.currency_id.compare_amounts(0, carryover_value) != 0:
                info_popup_data['carryover'] = self.format_value(carryover_value, figure_type='monetary')

                carryover_expression = line_expressions_map[carryover_expr_label]
                if carryover_expression.carryover_target:
                    info_popup_data['carryover_target'] = carryover_expression._get_carryover_target_expression(options).display_name
                # If it's not set, it means the carryover needs to target the same expression

            applied_carryover_value = target_line_res_dict.get('_applied_carryover_%s' % column_expr_label, {}).get('value', 0)
            if self.env.company.currency_id.compare_amounts(0, applied_carryover_value) != 0:
                info_popup_data['applied_carryover'] = self.format_value(applied_carryover_value, figure_type='monetary')
                info_popup_data['allow_carryover_audit'] = self.user_has_groups('base.group_no_one')
                info_popup_data['expression_id'] = line_expressions_map['_applied_carryover_%s' % column_expr_label]['id']

            # Handle manual edition popup
            edit_popup_data = {}
            if column_expression.engine == 'external' and column_expression.subformula \
                and len(options.get('multi_company', [])) < 2 \
                and (not options['available_vat_fiscal_positions'] or options['fiscal_position'] != 'all'):

                # Compute rounding for manual values
                rounding = None
                rounding_opt_match = re.search(r"\Wrounding\W*=\W*(?P<rounding>\d+)", column_expression.subformula)
                if rounding_opt_match:
                    rounding = int(rounding_opt_match.group('rounding'))
                elif figure_type == 'monetary':
                    rounding = self.env.company.currency_id.rounding

                if 'editable' in column_expression.subformula:
                    edit_popup_data = {
                        'column_group_key': column_data['column_group_key'],
                        'target_expression_id': column_expression.id,
                        'rounding': rounding,
                    }

                formatter_params = {'digits': rounding}
            else:
                formatter_params = {}

            # Build result
            blank_if_zero = column_expression.blank_if_zero or column_data.get('blank_if_zero')

            if column_value is None:
                formatted_name = ''
            else:
                formatted_name = self.format_value(
                    column_value,
                    figure_type=figure_type,
                    blank_if_zero=blank_if_zero,
                    **formatter_params
                )

            column_data = {
                'name': formatted_name,
                'style': 'white-space:nowrap; text-align:right;',
                'no_format': column_value,
                'column_group_key': options['columns'][len(columns)]['column_group_key'],
                'auditable': column_value is not None and column_expression.auditable,
                'expression_label': column_expr_label,
                'has_sublines': column_has_sublines,
                'report_line_id': line.id,
                'class': 'number' if isinstance(column_value, (int, float)) else '',
                'is_zero': column_value is None or (figure_type in ('float', 'integer', 'monetary') and self.is_zero(column_value, **formatter_params)),
            }

            if info_popup_data:
                column_data['info_popup_data'] = json.dumps(info_popup_data)

            if edit_popup_data:
                column_data['edit_popup_data'] = json.dumps(edit_popup_data)

            columns.append(column_data)

        return columns

    def _get_dynamic_lines(self, options, all_column_groups_expression_totals):
        if self.custom_handler_model_id:
            return self.env[self.custom_handler_model_name]._dynamic_lines_generator(self, options, all_column_groups_expression_totals)
        return []

    def _compute_expression_totals_for_each_column_group(self, expressions, options, groupby_to_expand=None, forced_all_column_groups_expression_totals=None, offset=0, limit=None):
        """
            Main computation function for static lines.

            :param expressions: The account.report.expression objects to evaluate.

            :param options: The options dict for this report, obtained from _get_options().

            :param groupby_to_expand: The full groupby string for the grouping we want to evaluate. If None, the aggregated value will be computed.
                                      For example, when evaluating a group by partner_id, which further will be divided in sub-groups by account_id,
                                      then id, the full groupby string will be: 'partner_id, account_id, id'.

            :param forced_all_column_groups_expression_totals: The expression totals already computed for this report, to which we will add the
                                                               new totals we compute for expressions (or update the existing ones if some
                                                               expressions are already in forced_all_column_groups_expression_totals). This is
                                                               a dict in the same format as returned by this function.
                                                               This parameter is for example used when adding manual values, where only
                                                               the expressions possibly depending on the new manual value
                                                               need to be updated, while we want to keep all the other values as-is.

            :param offset: The SQL offset to use when computing the result of these expressions. Used if self.load_more_limit is set, to handle
                           the load more feature.

            :param limit: The SQL limit to apply when computing these expressions' result. Used if self.load_more_limit is set, to handle
                          the load more feature.

            :return: dict(column_group_key, expressions_totals), where:
                - column group key is string identifying each column group in a unique way ; as in options['column_groups']
                - expressions_totals is a dict in the format returned by _compute_expression_totals_for_single_column_group
        """

        def add_expressions_to_groups(expressions_to_add, grouped_formulas, force_date_scope=None):
            """ Groups the expressions that should be computed together.
            """
            for expression in expressions_to_add:
                engine = expression.engine

                if engine not in grouped_formulas:
                    grouped_formulas[engine] = {}

                date_scope = force_date_scope or expression.date_scope
                groupby_data = expression.report_line_id._parse_groupby(groupby_to_expand=groupby_to_expand)

                grouping_key = (date_scope, groupby_data['current_groupby'], groupby_data['next_groupby'])

                if grouping_key not in grouped_formulas[engine]:
                    grouped_formulas[engine][grouping_key] = {}

                if expression.formula not in grouped_formulas[engine][grouping_key]:
                    grouped_formulas[engine][grouping_key][expression.formula] = expression
                else:
                    grouped_formulas[engine][grouping_key][expression.formula] |= expression

        if groupby_to_expand and any(not expression.report_line_id.groupby for expression in expressions):
            raise UserError(_("Trying to expand groupby results on lines without a groupby value."))

        # Group formulas for batching (when possible)
        grouped_formulas = {}
        for expression in expressions:
            add_expressions_to_groups(expression, grouped_formulas)

            if expression.engine == 'aggregation' and expression.subformula == 'cross_report':
                # Always expand aggregation expressions, in case their subexpressions are not in expressions parameter
                # (this can happen in cross report, or when auditing an individual aggregation expression)
                expanded_cross = expression._expand_aggregations()
                add_expressions_to_groups(expanded_cross, grouped_formulas, force_date_scope=expression.date_scope)

        # Treat each formula batch for each column group
        all_column_groups_expression_totals = {}
        for group_key, group_options in self._split_options_per_column_group(options).items():
            if forced_all_column_groups_expression_totals:
                forced_column_group_totals = forced_all_column_groups_expression_totals.get(group_key, None)
            else:
                forced_column_group_totals = None

            current_group_expression_totals = self._compute_expression_totals_for_single_column_group(
                group_options,
                grouped_formulas,
                forced_column_group_expression_totals=forced_column_group_totals,
                offset=offset,
                limit=limit,
            )
            all_column_groups_expression_totals[group_key] = current_group_expression_totals

        return all_column_groups_expression_totals

    def _split_options_per_column_group(self, options):
        """ Get a specific option dict per column group, each enforcing the comparison and horizontal grouping associated
        with the column group. Each of these options dict will contain a new key 'owner_column_group', with the column group key of the
        group it was generated for.

        :param options: The report options upon which the returned options be be based.

        :return:        A dict(column_group_key, options_dict), where column_group_key is the string identifying each column group (the keys
                        of options['column_groups'], and options_dict the generated options for this group.
        """
        options_per_group = {}
        for group_key in options['column_groups']:
            group_options = self._get_column_group_options(options, group_key)
            options_per_group[group_key] = group_options

        return options_per_group

    def _get_column_group_options(self, options, group_key):
        column_group = options['column_groups'][group_key]
        return {
            **options,
            **column_group['forced_options'],
            'forced_domain': options.get('forced_domain', []) + column_group['forced_domain'] + column_group['forced_options'].get('forced_domain', []),
            'owner_column_group': group_key,
        }

    def _compute_expression_totals_for_single_column_group(self, column_group_options, grouped_formulas, forced_column_group_expression_totals=None, offset=0, limit=None):
        """ Evaluates expressions for a single column group.

            :param column_group_options: The options dict obtained from _split_options_per_column_group() for the column group to evaluate.

            :param grouped_formulas: A dict(engine, formula_dict), where:
                                     - engine is a string identifying a report engine, in the same format as in account.report.expression's engine
                                       field's technical labels.
                                     - formula_dict is a dict in the same format as _compute_formula_batch's formulas_dict parameter,
                                       containing only aggregation formulas.

            :param forced_column_group_expression_totals: The expression totals previously computed, in the same format as this function's result.
                                                          If provided, the result of this function will be an updated version of this parameter,
                                                          recomputing the expressions in grouped_fomulas.

            :param offset: The SQL offset to use when computing the result of these expressions. Used if self.load_more_limit is set, to handle
                           the load more feature.

            :param limit: The SQL limit to apply when computing these expressions' result. Used if self.load_more_limit is set, to handle
                          the load more feature.

            :return: A dict(expression, value), where:
                     - expression is one of the account.report.expressions that got evaluated
                     - value is the result of that evaluation. Two cases are possible:
                        - if we're evaluating a groupby: value will then be a in the form [(groupby_key, groupby_val)], where
                            - groupby_key is the key used in the SQL GROUP BY clause to generate this result
                            - groupby_res: is the result of this group by element, as a res dict (see below)

                        - else: value will directly be the value computed for this expressions, as res dict (see below)

                        => res dict are dictionaries consisting of two keys:
                            - 'value': The value computed by the engine. Typically a float.
                            - 'has_sublines': [optional key, will default to False if absent]
                                              Whether or not this result corresponds to 1 or more subelements in the database (typically move lines).
                                              This is used to know whether an unfoldable line has results to unfold in the UI.
        """
        def inject_formula_results(formula_results, column_group_expression_totals):
            for (_formula, expressions), result in formula_results.items():
                for expression in expressions:
                    if expression.engine not in ('aggregation', 'external') and expression.subformula:
                        # aggregation subformulas behave differently (cross_report is markup ; if_below, if_above and force_between need evaluation)
                        # They are directly handled in aggregation engine
                        result_value_key = expression.subformula
                    else:
                        result_value_key = 'result'

                    # The expression might be signed, so we can't just access the dict key, and directly evaluate it instead.

                    if isinstance(result, list):
                        # Happens when expanding a groupby line, to compute its children.
                        # We then want to keep a list(grouping key, total) as the final result of each total
                        expression_value = []
                        expression_has_sublines = False
                        for key, result_dict in result:
                            expression_value.append((key, safe_eval(result_value_key, result_dict)))
                            expression_has_sublines = expression_has_sublines or result_dict.get('has_sublines')
                    else:
                        # For non-groupby lines, we directly set the total value for the line.
                        expression_value = safe_eval(result_value_key, result)
                        expression_has_sublines = result.get('has_sublines')

                    column_group_expression_totals[expression] = {
                        'value': expression_value,
                        'has_sublines': expression_has_sublines,
                    }

        # Batch each engine that can be
        column_group_expression_totals = forced_column_group_expression_totals or {}
        batchable_engines = [
            selection_val[0]
            for selection_val in self.env['account.report.expression']._fields['engine'].selection
            if selection_val[0] != 'aggregation'
        ]
        for engine in batchable_engines:
            for (date_scope, current_groupby, next_groupby), formulas_dict in grouped_formulas.get(engine, {}).items():
                formula_results = self._compute_formula_batch(column_group_options, engine, date_scope, formulas_dict, current_groupby, next_groupby, offset=offset, limit=limit)
                inject_formula_results(formula_results, column_group_expression_totals)

        # Now that everything else has been computed, resolve aggregation expressions
        # (they can't be treated as the other engines, as if we batch them per date_scope, we'll not be able
        # to compute expressions depending on other expressions with a different date scope).
        aggregation_formulas_dict = {}
        for formulas_dict in grouped_formulas.get('aggregation', {}).values():
            for formula, expressions in formulas_dict.items():
                # date_scope and group_by are ignored by this engine, so we merge every grouped entry into a common dict
                # (date_scope can however be used with cross_report feature, but it's handled before this)
                if formula in aggregation_formulas_dict:
                    aggregation_formulas_dict[formula] |= expressions
                else:
                    aggregation_formulas_dict[formula] = expressions

        if aggregation_formulas_dict:
            aggregation_formula_results = self._compute_totals_no_batch_aggregation(column_group_options, aggregation_formulas_dict, column_group_expression_totals)
            inject_formula_results(aggregation_formula_results, column_group_expression_totals)

        return column_group_expression_totals

    def _compute_totals_no_batch_aggregation(self, column_group_options, formulas_dict, other_expressions_totals):
        """ Computes expression totals for 'aggregation' engine, after all other engines have been evaluated.

        :param column_group_options: The options for the column group being evaluated, as obtained from _split_options_per_column_group.

        :param formulas_dict: A dict in the same format as _compute_formula_batch's formulas_dict parameter, containing only aggregation formulas.

        :param other_expressions_totals: The expressions_totals obtained after computing all non-aggregation engines, whose values will be used
                                         to evaluate the aggregations. This is a dict is the same format as
                                         _compute_expression_totals_for_single_column_group's result (the only difference being it does not contain
                                         any aggregation expression yet).

        :return : A dict((formula, expressions), result), where result is in the form {'result': numeric_value}
        """
        def _resolve_subformula_on_dict(result, subformula):
            for key in subformula.split('.'):
                result = result[key]
            return result

        evaluation_dict = {}
        for expression, expression_res in other_expressions_totals.items():
            if expression.report_line_id.code:
                evaluation_dict.setdefault(expression.report_line_id.code, {})
                evaluation_dict[expression.report_line_id.code][expression.label] = self.env.company.currency_id.round(expression_res['value'])

        # Complete evaluation_dict with the formulas of uncomputed aggregation lines
        aggregations_terms_to_evaluate = set() # Those terms are part of the formulas to evaluate; we know they will get a value eventually
        for formula, expressions in formulas_dict.items():
            for expression in expressions:
                if expression.report_line_id.code:
                    aggregations_terms_to_evaluate.add(f"{expression.report_line_id.code}.{expression.label}")
                    evaluation_dict.setdefault(expression.report_line_id.code, {})
                    if not expression.subformula or not re.match(r"if_(above|below|between)\(.*\)", expression.subformula):
                        # Expressions with bounds cannot be replaced by their formula in formulas calling them (otherwize, bounds would be ignored).
                        evaluation_dict[expression.report_line_id.code][expression.label] = formula

        rslt = {}
        to_treat = [(formula, formula) for formula in formulas_dict.keys()] # Formed like [(expanded formula, original unexpanded formula)]
        term_separator_regex = r'[ ()+/*-]'
        term_replacement_regex = r"(^|(?<=" + term_separator_regex + r"))%s((?="+ term_separator_regex + r")|$)"
        while to_treat:
            formula, unexpanded_formula = to_treat.pop(0)

            # Evaluate the formula
            terms_to_eval = [term for term in re.split(term_separator_regex, formula) if not re.match(r'^[0-9.]*$', term)]

            if terms_to_eval:
                # The formula can't be evaluated as-is. Replace the terms by their value or formula,
                # and enqueue the formula back; it'll be tried anew later in the loop.
                for term in terms_to_eval:
                    try:
                        expanded_term = _resolve_subformula_on_dict(evaluation_dict, term)
                    except KeyError:
                        if term in aggregations_terms_to_evaluate:
                            # Then, the term is probably an aggregation with bounds that still needs to be computed. We need to keep on looping
                            continue
                        else:
                            raise UserError(_("Could not expand term %s while evaluating formula %s", term, unexpanded_formula))
                    formula = re.sub(term_replacement_regex % re.escape(term), f'({expanded_term})', formula)

                to_treat.append((formula, unexpanded_formula))

            else:
                # The formula contains only digits and operators; it can be evaluated
                try:
                    formula_result = expr_eval(formula)
                except ZeroDivisionError:
                    # Arbitrary choice; for clarity of the report. A 0 division could typically happen when there is no result in the period.
                    formula_result = 0

                for expression in formulas_dict[unexpanded_formula]:
                    expression_result = self._aggregation_apply_bounds(column_group_options, expression, formula_result)
                    rslt[(unexpanded_formula, expression)] = {'result': expression_result}

                    if expression.report_line_id.code:
                        # If lines using this formula have a code, they are probably used in other formulas.
                        # We need to make the result of our computation available to them, as they are still waiting in to_treat to be evaluated.
                        evaluation_dict[expression.report_line_id.code][expression.label] = expression_result

        return rslt

    def _aggregation_apply_bounds(self, column_group_options, aggregation_expr, unbound_value):
        """ Applies the bounds of the provided aggregation expression to an unbounded value that got computed for it and returns the result.
        Bounds can be defined as subformulas of aggregation expressions, with the following possible values:

            - if_above(CUR(bound_value)):
                                    => Result will be 0 if it's <= the provided bound value; else it'll be unbound_value

            - if_below(CUR(bound_value)):
                                    => Result will be 0 if it's >= the provided bound value; else it'll be unbound_value

            - if_between(CUR(bound_value1), CUR(bound_value2)):
                                    => Result will be unbound_value if it's strictly between the provided bounds. Else, it will
                                       be brought back to the closest bound.

            (where CUR is a currency code, and bound_value* are float amounts in CUR currency)
        """
        if aggregation_expr.subformula and aggregation_expr.subformula != 'cross_report':
            # So an expression can't have bounds and be cross_reports, for simplicity.
            # To do that, just split the expression in two parts.
            company_currency = self.env.company.currency_id
            date_to = column_group_options['date']['date_to']

            match = re.match(
                r"(?P<criterium>\w*)"
                r"\((?P<currency_1>[A-Z]{3})\((?P<amount_1>[-]?\d+(\.\d+)?)\)"
                r"(,(?P<currency_2>[A-Z]{3})\((?P<amount_2>[-]?\d+(\.\d+)?)\))?\)$",
                aggregation_expr.subformula.replace(' ', '')
            )
            group_values = match.groupdict()

            # Convert the provided bounds into company currency
            currency_code_1 = group_values.get('currency_1')
            currency_code_2 = group_values.get('currency_2')
            currency_codes = [
                currency_code
                for currency_code in [currency_code_1, currency_code_2]
                if currency_code and currency_code != company_currency.name
            ]

            if currency_codes:
                currencies = self.env['res.currency'].with_context(active_test=False).search([('name', 'in', currency_codes)])
            else:
                currencies = self.env['res.currency']

            amount_1 = float(group_values['amount_1'] or 0)
            amount_2 = float(group_values['amount_2'] or 0)
            for currency in currencies:
                if currency != company_currency:
                    if currency.name == currency_code_1:
                        amount_1 = currency._convert(amount_1, company_currency, self.env.company, date_to)
                    if amount_2 and currency.name == currency_code_2:
                        amount_2 = currency._convert(amount_2, company_currency, self.env.company, date_to)

            # Evaluate result
            criterium = group_values['criterium']
            if criterium == 'if_below':
                if company_currency.compare_amounts(unbound_value, amount_1) >= 0:
                    return 0
            elif criterium == 'if_above':
                if company_currency.compare_amounts(unbound_value, amount_1) <= 0:
                    return 0
            elif criterium == 'if_between':
                if company_currency.compare_amounts(unbound_value, amount_1) < 0 or company_currency.compare_amounts(unbound_value, amount_2) > 0:
                    return 0
            else:
                raise UserError(_("Unknown bound criterium: %s", criterium))

        return unbound_value

    def _compute_formula_batch(self, column_group_options, formula_engine, date_scope, formulas_dict, current_groupby, next_groupby, offset=0, limit=None):
        """ Evaluates a batch of formulas.

        :param column_group_options: The options for the column group being evaluated, as obtained from _split_options_per_column_group.

        :param formula_engine: A string identifying a report engine. Must be one of account.report.expression's engine field's technical labels.

        :param date_scope: The date_scope under which to evaluate the fomulas. Must be one of account.report.expression's date_scope field's
                           technical labels.

        :param formulas_dict: A dict in the dict(formula, expressions), where:
                                - formula: a formula to be evaluated with the engine referred to by parent dict key
                                - expressions: a recordset of all the expressions to evaluate using formula (possibly with distinct subformulas)

        :param current_groupby: The groupby to evaluate, or None if there isn't any. In case of multi-level groupby, only contains the element
                                that needs to be computed (so, if unfolding a line doing 'partner_id,account_id,id'; current_groupby will only be
                                'partner_id'). Subsequent groupby will be in next_groupby.

        :param next_groupby: Full groupby string of the groups that will have to be evaluated next for these expressions, or None if there isn't any.
                             For example, in the case depicted in the example of current_groupby, next_groupby will be 'account_id,id'.

        :param offset: The SQL offset to use when computing the result of these expressions.

        :param limit: The SQL limit to apply when computing these expressions' result.

        :return: Two cases are possible:
            - if we're not computing a groupby: the result will a dict(formula, expressions)

        """
        engine_function_name = f'_compute_formula_batch_with_engine_{formula_engine}'
        return getattr(self, engine_function_name)(
            column_group_options, date_scope, formulas_dict, current_groupby, next_groupby,
            offset=offset, limit=limit
        )

    def _compute_formula_batch_with_engine_tax_tags(self, options, date_scope, formulas_dict, current_groupby, next_groupby, offset=0, limit=None):
        """ Report engine.

        The formulas made for this report simply consist of a tag label. When an expression using this engine is created, it also creates two
        account.account.tag objects, namely -tag and +tag, where tag is the chosen formula. The balance of the expressions using this engine is
        computed by gathering all the move lines using their tags, and applying the sign of their tag to their balance, together with a -1 factor
        if the tax_tag_invert field of the move line is True.

        This engine does not support any subformula.
        """
        self._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))
        all_expressions = self.env['account.report.expression']
        for expressions in formulas_dict.values():
            all_expressions |= expressions
        tags = all_expressions._get_matching_tags()

        currency_table_query = self.env['res.currency']._get_query_currency_table(options)
        groupby_sql = f'account_move_line.{current_groupby}' if current_groupby else None
        tables, where_clause, where_params = self._query_get(options, date_scope)
        tail_query, tail_params = self._get_engine_query_tail(offset, limit)
        if self.pool['account.account.tag'].name.translate:
            lang = self.env.user.lang or get_lang(self.env).code
            acc_tag_name = f"COALESCE(acc_tag.name->>'{lang}', acc_tag.name->>'en_US')"
        else:
            acc_tag_name = 'acc_tag.name'
        sql = f"""
            SELECT
                SUBSTRING({acc_tag_name}, 2, LENGTH({acc_tag_name}) - 1) AS formula,
                SUM(ROUND(COALESCE(account_move_line.balance, 0) * currency_table.rate, currency_table.precision)
                    * CASE WHEN acc_tag.tax_negate THEN -1 ELSE 1 END
                    * CASE WHEN account_move_line.tax_tag_invert THEN -1 ELSE 1 END
                ) AS balance,
                COUNT(account_move_line.id) AS aml_count
                {f', {groupby_sql} AS grouping_key' if groupby_sql else ''}

            FROM {tables}

            JOIN account_account_tag_account_move_line_rel aml_tag
                ON aml_tag.account_move_line_id = account_move_line.id
            JOIN account_account_tag acc_tag
                ON aml_tag.account_account_tag_id = acc_tag.id
                AND acc_tag.id IN %s
            JOIN {currency_table_query}
                ON currency_table.company_id = account_move_line.company_id

            WHERE {where_clause}

            GROUP BY SUBSTRING({acc_tag_name}, 2, LENGTH({acc_tag_name}) - 1)
                {f', {groupby_sql}' if groupby_sql else ''}

            {tail_query}
        """

        params = [tuple(tags.ids)] + where_params + tail_params
        self._cr.execute(sql, params)

        empty_val = [] if current_groupby else {'result': 0, 'has_sublines': False}
        rslt = {formula_expr: empty_val for formula_expr in formulas_dict.items()}
        for query_res in self._cr.dictfetchall():

            formula = query_res['formula']
            rslt_dict = {'result': query_res['balance'], 'has_sublines': query_res['aml_count'] > 0}
            for formula_expr in formulas_dict[formula]:
                if current_groupby:
                    rslt[(formula, formula_expr)].append((query_res['grouping_key'], rslt_dict))
                else:
                    rslt[(formula, formula_expr)] = rslt_dict

        return rslt

    def _compute_formula_batch_with_engine_domain(self, options, date_scope, formulas_dict, current_groupby, next_groupby, offset=0, limit=None):
        """ Report engine.

        Formulas made for this engine consist of a domain on account.move.line. Only those move lines will be used to compute the result.

        This engine supports a few subformulas, each returning a slighlty different result:
        - sum: the result will be sum of the matched move lines' balances

        - sum_if_pos: the result will be the same as sum only if it's positive; else, it will be 0

        - sum_if_neg: the result will be the same as sum only if it's negative; else, it will be 0

        - count_rows: the result will be the number of sublines this expression has. If the parent report line has no groupby,
                      then it will be the number of matching amls. If there is a groupby, it will be the number of distinct grouping
                      keys at the first level of this groupby (so, if groupby is 'partner_id, account_id', the number of partners).
        """
        def _format_result_depending_on_groupby(formula_rslt):
            if not current_groupby:
                if formula_rslt:
                    # There should be only one element in the list; we only return its totals (a dict) ; so that a list is only returned in case
                    # of a groupby being unfolded.
                    return formula_rslt[0][1]
                else:
                    # No result at all
                    return {
                        'sum': 0,
                        'sum_if_pos': 0,
                        'sum_if_neg': 0,
                        'count_rows': 0,
                        'has_sublines': False,
                    }
            return formula_rslt

        self._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        groupby_sql = f'account_move_line.{current_groupby}' if current_groupby else None
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        rslt = {}

        for formula, expressions in formulas_dict.items():
            line_domain = literal_eval(formula)
            tables, where_clause, where_params = self._query_get(options, date_scope, domain=line_domain)

            tail_query, tail_params = self._get_engine_query_tail(offset, limit)
            query = f"""
                SELECT
                    COALESCE(SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)), 0.0) AS sum,
                    COUNT(DISTINCT account_move_line.{next_groupby.split(',')[0] if next_groupby else 'id'}) AS count_rows
                    {f', {groupby_sql} AS grouping_key' if groupby_sql else ''}
                FROM {tables}
                JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause}
                {f' GROUP BY {groupby_sql}' if groupby_sql else ''}
                {tail_query}
            """

            # Fetch the results.
            formula_rslt = []
            self._cr.execute(query, where_params + tail_params)
            all_query_res = self._cr.dictfetchall()

            total_sum = 0
            for query_res in all_query_res:
                res_sum = query_res['sum']
                total_sum += res_sum
                totals = {
                    'sum': res_sum,
                    'sum_if_pos': 0,
                    'sum_if_neg': 0,
                    'count_rows': query_res['count_rows'],
                    'has_sublines': query_res['count_rows'] > 0,
                }
                formula_rslt.append((query_res.get('grouping_key', None), totals))

            # Handle sum_if_pos, -sum_if_pos, sum_if_neg and -sum_if_neg
            expressions_by_sign_policy = defaultdict(lambda: self.env['account.report.expression'])
            for expression in expressions:
                subformula_without_sign = expression.subformula.replace('-', '').strip()
                if subformula_without_sign in ('sum_if_pos', 'sum_if_neg'):
                    expressions_by_sign_policy[subformula_without_sign] += expression
                else:
                    expressions_by_sign_policy['no_sign_check'] += expression

            # Then we have to check the total of the line and only give results if its sign matches the desired policy.
            # This is important for groupby managements, for which we can't just check the sign query_res by query_res
            if expressions_by_sign_policy['sum_if_pos'] or expressions_by_sign_policy['sum_if_neg']:
                sign_policy_with_value = 'sum_if_pos' if self.env.company.currency_id.compare_amounts(total_sum, 0.0) >= 0 else 'sum_if_neg'
                # >= instead of > is intended; usability decision: 0 is considered positive

                formula_rslt_with_sign = [(grouping_key, {**totals, sign_policy_with_value: totals['sum']}) for grouping_key, totals in formula_rslt]

                for sign_policy in ('sum_if_pos', 'sum_if_neg'):
                    policy_expressions = expressions_by_sign_policy[sign_policy]

                    if policy_expressions:
                        if sign_policy == sign_policy_with_value:
                            rslt[(formula, policy_expressions)] = _format_result_depending_on_groupby(formula_rslt_with_sign)
                        else:
                            rslt[(formula, policy_expressions)] = _format_result_depending_on_groupby([])

            if expressions_by_sign_policy['no_sign_check']:
                rslt[(formula, expressions_by_sign_policy['no_sign_check'])] = _format_result_depending_on_groupby(formula_rslt)

        return rslt

    def _compute_formula_batch_with_engine_account_codes(self, options, date_scope, formulas_dict, current_groupby, next_groupby, offset=0, limit=None):
        r""" Report engine.

        Formulas made for this engine target account prefixes. Each of the prefix used in the formula will be evaluated as the sum of the move
        lines made on the accounts matching it. Those prefixes can be used together with arithmetic operations to perform them on the obtained
        results.
        Example: '123 - 456' will substract the balance of all account starting with 456 from the one of all accounts starting with 123.

        It is also possible to exclude some subprefixes, with \ operator.
        Example: '123\(1234)' will match prefixes all accounts starting with '123', except the ones starting with '1234'

        To only match the balance of an account is it's positive (debit) or negative (credit), the letter D or C can be put just next to the prefix:
        Example '123D': will give the total balance of accounts starting with '123' if it's positive, else it will be evaluated as 0.

        Multiple subprefixes can be excluded if needed.
        Example: '123\(1234,1236)

        All these syntaxes can be mixed together.
        Example: '123D\(1235) + 56 - 416C'

        Note: if C or D character needs to be part of the prefix, it is possible to differentiate them of debit and credit match characters
        by using an empty prefix exclusion.
        Example 1: '123D\' will take the total balance of accounts starting with '123D'
        Example 2: '123D\C' will return the balance of accounts starting with '123D' if it's negative, 0 otherwise.
        """
        self._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        # Gather the account code prefixes to compute the total from
        prefix_details_by_formula = {}  # in the form {formula: [(1, prefix1), (-1, prefix2)]}
        prefixes_to_compute = set()
        for formula in formulas_dict:
            prefix_details_by_formula[formula] = []
            for token in ACCOUNT_CODES_ENGINE_SPLIT_REGEX.split(formula.replace(' ', '')):
                if token:
                    token_match = ACCOUNT_CODES_ENGINE_TERM_REGEX.match(token)

                    if not token_match:
                        raise UserError(_("Invalid token '%s' in account_codes formula '%s'", token, formula))

                    parsed_token = token_match.groupdict()

                    if not parsed_token:
                        raise UserError(_("Could not parse account_code formula from token '%s'", token))

                    multiplicator = -1 if parsed_token['sign'] == '-' else 1
                    excluded_prefixes_match = token_match['excluded_prefixes']
                    excluded_prefixes = excluded_prefixes_match.split(',') if excluded_prefixes_match else []
                    prefix = token_match['prefix']

                    # We group using both prefix and excluded_prefixes as keys, for the case where two expressions would
                    # include the same prefix, but exlcude different prefixes (example 104\(1041) and 104\(1042))
                    prefix_key = (prefix, *excluded_prefixes)
                    prefix_details_by_formula[formula].append((multiplicator, prefix_key, token_match['balance_character']))
                    prefixes_to_compute.add((prefix, tuple(excluded_prefixes)))

        # Create the subquery for the WITH linking our prefixes with account.account entries
        all_prefixes_queries = []
        prefix_params = []
        company_ids = [comp_opt['id'] for comp_opt in options.get('multi_company', self.env.company)]
        for prefix, excluded_prefixes in prefixes_to_compute:
            account_domain = [('company_id', 'in', company_ids), ('code', '=like', f'{prefix}%')]
            excluded_prefixes_domains = []

            for excluded_prefix in excluded_prefixes:
                excluded_prefixes_domains.append([('code', '=like', f'{excluded_prefix}%')])

            if excluded_prefixes_domains:
                account_domain.append('!')
                account_domain += osv.expression.OR(excluded_prefixes_domains)

            prefix_tables, prefix_where_clause, prefix_where_params = self.env['account.account']._where_calc(account_domain).get_sql()

            prefix_params.append(prefix)
            for excluded_prefix in excluded_prefixes:
                prefix_params.append(excluded_prefix)

            prefix_select_query = ', '.join(['%s'] * (len(excluded_prefixes) + 1)) # +1 for prefix
            prefix_select_query = f'ARRAY[{prefix_select_query}]'

            all_prefixes_queries.append(f"""
                SELECT
                    {prefix_select_query} AS prefix,
                    account_account.id AS account_id
                FROM {prefix_tables}
                WHERE {prefix_where_clause}
            """)
            prefix_params += prefix_where_params

        # Run main query
        tables, where_clause, where_params = self._query_get(options, date_scope)
        where_params = prefix_params + where_params

        currency_table_query = self.env['res.currency']._get_query_currency_table(options)
        extra_groupby_sql = f', account_move_line.{current_groupby}' if current_groupby else ''
        extra_select_sql = f', account_move_line.{current_groupby} AS grouping_key' if current_groupby else ''
        tail_query, tail_params = self._get_engine_query_tail(offset, limit)

        query = f"""
            WITH accounts_by_prefix AS ({' UNION ALL '.join(all_prefixes_queries)})

            SELECT
                accounts_by_prefix.account_id,
                accounts_by_prefix.prefix,
                SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS sum,
                COUNT(account_move_line.id) AS aml_count
                {extra_select_sql}
            FROM {tables}
            JOIN accounts_by_prefix ON accounts_by_prefix.account_id = account_move_line.account_id
            JOIN {currency_table_query} ON currency_table.company_id = account_move_line.company_id
            WHERE {where_clause}
            GROUP BY accounts_by_prefix.prefix,accounts_by_prefix.account_id{extra_groupby_sql}
            {tail_query}
        """
        self._cr.execute(query, where_params + tail_params)

        # Parse result
        rslt = {}

        res_by_prefix_account_id = {}
        for query_res in self._cr.dictfetchall():
            # Done this way so that we can run similar code for groupby and non-groupby
            grouping_key = query_res['grouping_key'] if current_groupby else None
            prefix_key = tuple(query_res['prefix'])
            res_by_prefix_account_id.setdefault(prefix_key, {})\
                                    .setdefault(query_res['account_id'], [])\
                                    .append((grouping_key, {'result': query_res['sum'], 'has_sublines': query_res['aml_count'] > 0}))

        for formula, prefix_details in prefix_details_by_formula.items():
            rslt_key = (formula, formulas_dict[formula])
            rslt_destination = rslt.setdefault(rslt_key, [] if current_groupby else {'result': 0, 'has_sublines': False})
            for multiplicator, prefix_key, balance_character in prefix_details:
                res_by_account_id = res_by_prefix_account_id.get(prefix_key, {})

                for account_results in res_by_account_id.values():
                    account_total_value = sum(group_val['result'] for (group_key, group_val) in account_results)
                    comparator = self.env.company.currency_id.compare_amounts(account_total_value, 0.0)

                    # Manage balance_character.
                    if not balance_character or (balance_character == 'D' and comparator >= 0) or (balance_character == 'C' and comparator < 0):

                        for group_key, group_val in account_results:
                            rslt_group = {
                                **group_val,
                                'result': multiplicator * group_val['result'],
                            }

                            if current_groupby:
                                rslt_destination.append((group_key, rslt_group))
                            else:
                                rslt_destination['result'] += rslt_group['result']
                                rslt_destination['has_sublines'] = rslt_destination['has_sublines'] or rslt_group['has_sublines']

        return rslt

    def _compute_formula_batch_with_engine_external(self, options, date_scope, formulas_dict, current_groupby, next_groupby, offset=0, limit=None):
        """ Report engine.

        This engine computes its result from the account.report.external.value objects that are linked to the expression.

        Two different formulas are possible:
        - sum: if the result must be the sum of all the external values in the period.
        - most_recent: it the result must be the value of the latest external value in the period.

        No subformula is allowed for this engine.
        """
        self._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        if current_groupby or next_groupby or offset or limit:
            raise UserError(_("'external' engine does not support groupby, limit nor offset."))

        # Date clause
        date_from, date_to, dummy = self._get_date_bounds_info(options, date_scope)
        external_value_domain = [('date', '<=', date_to)]
        if date_from:
            external_value_domain.append(('date', '>=', date_from))

        # Company clause
        multi_company_opt = options.get('multi_company', [{'id': self.env.company.id}])
        external_value_domain.append(('company_id', 'in', [x['id'] for x in multi_company_opt]))

        # Fiscal Position clause
        fpos_option = options['fiscal_position']
        if fpos_option == 'domestic':
            external_value_domain.append(('foreign_vat_fiscal_position_id', '=', False))
        elif fpos_option != 'all':
            # Then it's a fiscal position id
            external_value_domain.append(('foreign_vat_fiscal_position_id', '=', int(fpos_option)))

        # Do the computation
        dummy, where_clause, where_params = self.env['account.report.external.value']._where_calc(external_value_domain).get_sql()
        currency_table_query = self.env['res.currency']._get_query_currency_table(options)
        queries = []
        query_params = []
        for formula, expressions in formulas_dict.items():
            query_end = ''
            if formula == 'most_recent':
                query_end = """
                    GROUP BY date
                    ORDER BY date DESC
                    LIMIT 1
                """

            for expression in expressions:
                queries.append(f"""
                    SELECT
                        %s,
                        COALESCE(SUM(COALESCE(ROUND(CAST(value AS numeric) * currency_table.rate, currency_table.precision), 0)), 0)
                    FROM account_report_external_value
                        JOIN {currency_table_query} ON currency_table.company_id = account_report_external_value.company_id
                    WHERE {where_clause} AND target_report_expression_id = %s
                    {query_end}
                """)
                query_params += [
                    expression.id,
                    *where_params,
                    expression.id,
                ]
        query = '(' + ') UNION ALL ('.join(queries) + ')'
        self._cr.execute(query, query_params)
        query_results = self._cr.fetchall()

        # Convert to dict to have expression ids as keys
        query_results_dict = dict(query_results)
        # Build result dict
        rslt = {}
        for formula, expressions in formulas_dict.items():
            for expression in expressions:
                expression_value = query_results_dict.get(expression.id)
                # If expression_value is None, we have no previous value for this expression (set default at 0.0)
                rslt[(formula, expression)] = {'result': expression_value or 0.0, 'has_sublines': False}

        return rslt

    def _compute_formula_batch_with_engine_custom(self, options, date_scope, formulas_dict, current_groupby, next_groupby, offset=0, limit=None):
        self._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        rslt = {}
        for formula, expressions in formulas_dict.items():
            custom_engine_function = self._get_custom_report_function(formula, 'custom_engine')
            rslt[(formula, expressions)] = custom_engine_function(
                expressions, options, date_scope, current_groupby, next_groupby, offset=offset, limit=limit)
        return rslt

    def _get_engine_query_tail(self, offset, limit):
        """ Helper to generate the OFFSET, LIMIT and ORDER conditions of formula engines' queries.
        """
        params = []
        query_tail = ""

        if offset:
            query_tail += " OFFSET %s"
            params.append(offset)

        if limit:
            query_tail += " LIMIT %s"
            params.append(limit)

        return query_tail, params

    def _generate_carryover_external_values(self, options):
        """ Generates the account.report.external.value objects corresponding to this report's carryover under the provided options.

        In case of multicompany setup, we need to split the carryover per company, for ease of audit, and so that the carryover isn't broken when
        a company leaves a tax unit.

        We first generate the carryover for the wholy-aggregated report, so that we can see what final result we want.
        Indeed due to force_between, if_above and if_below conditions, each carryover might be different from the sum of the individidual companies'
        carryover values. To handle this case, we generate each company's carryover values separately, then do a carryover adjustment on the
        main company (main for tax units, first one selected else) in order to bring their total to the result we computed for the whole unit.
        """
        self.ensure_one()

        if len(options['column_groups']) > 1:
            # The options must be forged in order to generate carryover values. Entering this conditions means this hasn't been done in the right way.
            raise UserError(_("Carryover can only be generated for a single column group."))

        # Get the expressions to evaluate from the report
        carryover_expressions = self.line_ids.expression_ids.filtered(lambda x: x.label.startswith('_carryover_'))
        expressions_to_evaluate = carryover_expressions._expand_aggregations()

        # Expression totals for all selected companies
        expression_totals_per_col_group = self._compute_expression_totals_for_each_column_group(expressions_to_evaluate, options)
        expression_totals = expression_totals_per_col_group[list(options['column_groups'].keys())[0]]
        carryover_values = {expression: expression_totals[expression]['value'] for expression in carryover_expressions}

        if len(options.get('multi_company', [])) < 2:
            company = self.env['res.company'].browse(self.get_report_company_ids(options))
            self._create_carryover_for_company(options, company, {expr: result for expr, result in carryover_values.items()})
        else:
            multi_company_carryover_values_sum = defaultdict(lambda: 0)

            column_group_key = next(col_group_key for col_group_key in options['column_groups'])
            for company_opt in options['multi_company']:
                company = self.env['res.company'].browse(company_opt['id'])
                company_options = {**options, 'multi_company': [{'id': company.id, 'name': company.name}]}
                company_expressions_totals = self._compute_expression_totals_for_each_column_group(expressions_to_evaluate, company_options)
                company_carryover_values = {expression: company_expressions_totals[column_group_key][expression]['value'] for expression in carryover_expressions}
                self._create_carryover_for_company(options, company, company_carryover_values)

                for carryover_expr, carryover_val in company_carryover_values.items():
                    multi_company_carryover_values_sum[carryover_expr] += carryover_val

            # Adjust multicompany amounts on main company
            main_company = self._get_sender_company_for_export(options)
            for expr in carryover_expressions:
                difference = carryover_values[expr] - multi_company_carryover_values_sum[expr]
                self._create_carryover_for_company(options, main_company, {expr: difference}, label=_("Carryover adjustment for tax unit"))

    @api.model
    def _get_sender_company_for_export(self, options):
        """ Return the sender company when generating an export file from this report.
            :return: self.env.company if not using a tax unit, else the main company of that unit
        """
        if options.get('tax_unit', 'company_only') != 'company_only':
            tax_unit = self.env['account.tax.unit'].browse(options['tax_unit'])
            return tax_unit.main_company_id

        return self.env.company

    def _create_carryover_for_company(self, options, company, carryover_per_expression, label=None):
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        fiscal_position_opt = options['fiscal_position']

        if carryover_per_expression and fiscal_position_opt == 'all':
            # Not supported, as it wouldn't make sense, and would make the code way more complicated (because of if_below/if_above/force_between,
            # just in the same way as it is explained below for multi company)
            raise UserError(_("Cannot generate carryover values for all fiscal positions at once!"))

        external_values_create_vals = []
        for expression, carryover_value in carryover_per_expression.items():
            if not company.currency_id.is_zero(carryover_value):
                target_expression = expression._get_carryover_target_expression(options)
                external_values_create_vals.append({
                    'name': label or _("Carryover from %s to %s", format_date(self.env, date_from), format_date(self.env, date_to)),
                    'value': carryover_value,
                    'date': date_to,
                    'target_report_expression_id': target_expression.id,
                    'foreign_vat_fiscal_position_id': fiscal_position_opt if isinstance(fiscal_position_opt, int) else None,
                    'carryover_origin_expression_label': expression.label,
                    'carryover_origin_report_line_id': expression.report_line_id.id,
                    'company_id': company.id,
                })

        self.env['account.report.external.value'].create(external_values_create_vals)

    def get_default_report_filename(self, extension):
        """The default to be used for the file when downloading pdf,xlsx,..."""
        self.ensure_one()
        return f"{self.name.lower().replace(' ', '_')}.{extension}"

    def execute_action(self, options, params=None):
        action_id = int(params.get('actionId'))
        action = self.env['ir.actions.actions'].sudo().browse([action_id])
        action_type = action.type
        action = self.env[action.type].sudo().browse([action_id])
        action_read = clean_action(action.read()[0], env=action.env)

        if action_type == 'ir.actions.client':
            # Check if we are opening another report. If so, generate options for it from the current options.
            if action.tag == 'account_report':
                target_report = self.env['account.report'].browse(ast.literal_eval(action_read['context'])['report_id'])
                new_options = target_report._get_options(previous_options=options)
                action_read.update({'params': {'options': new_options, 'ignore_session': 'read'}})

        if params.get('id'):
            # Add the id of the calling object in the action's context
            if isinstance(params['id'], int):
                # id of the report line might directly be the id of the model we want.
                model_id = params['id']
            else:
                # It can also be a generic account.report id, as defined by _get_generic_line_id
                model_id = self._get_model_info_from_id(params['id'])[1]

            context = action_read.get('context') and literal_eval(action_read['context']) or {}
            context.setdefault('active_id', model_id)
            action_read['context'] = context

        return action_read

    def action_audit_cell(self, options, params):
        report_line = self.env['account.report.line'].browse(params['report_line_id'])
        expression_label = params['expression_label']
        expression = report_line.expression_ids.filtered(lambda x: x.label == expression_label)
        column_group_options = self._get_column_group_options(options, params['column_group_key'])

        # Audit of external values
        if expression.engine == 'external':
            date_from, date_to, dummy = self._get_date_bounds_info(column_group_options, expression.date_scope)
            external_values_domain = [('target_report_expression_id', '=', expression.id), ('date', '<=', date_to)]
            if date_from:
                external_values_domain.append(('date', '>=', date_from))

            if expression.formula == 'most_recent':
                tables, where_clause, where_params = self.env['account.report.external.value']._where_calc(external_values_domain).get_sql()
                self._cr.execute(f"""
                    SELECT ARRAY_AGG(id)
                    FROM {tables}
                    WHERE {where_clause}
                    GROUP BY date
                    ORDER BY date DESC
                    LIMIT 1
                """, where_params)
                record_ids = self._cr.fetchone()[0]
                external_values_domain = [('id', 'in', record_ids)]

            return {
                'name': _("Manual values"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.report.external.value',
                'view_mode': 'list',
                'views': [(False, 'list')],
                'domain': external_values_domain,
            }

        # Audit of move lines
        # If we're auditing a groupby line, we need to make sure to restrict the result of what we audit to the right group values
        column = next(col for col in report_line.report_id.column_ids if col.expression_label == expression_label)
        if column.custom_audit_action_id:
            action_dict = column.custom_audit_action_id._get_action_dict()
        else:
            action_dict = {
                'name': _("Journal Items"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move.line',
                'view_mode': 'list',
                'views': [(False, 'list')],
            }

        action = clean_action(action_dict, env=self.env)
        action['domain'] = self._get_audit_line_domain(column_group_options, expression, params)
        return action

    def _get_audit_line_domain(self, column_group_options, expression, params):
        calling_line_dict_id = params['calling_line_dict_id']
        parsed_line_dict_id = self._parse_line_id(calling_line_dict_id)
        groupby_domain = []
        for markup, dummy, model_id in parsed_line_dict_id:
            groupby_match = re.match("groupby:(?P<groupby_field>.*)", markup)
            if groupby_match:
                groupby_domain.append((groupby_match['groupby_field'], '=', model_id))

        # Aggregate all domains per date scope, then create the final domain.
        audit_or_domains_per_date_scope = {}
        for expression_to_audit in expression._expand_aggregations():
            expression_domain = self._get_expression_audit_aml_domain(expression_to_audit, column_group_options)

            if expression_domain is None:
                continue

            audit_or_domains = audit_or_domains_per_date_scope.setdefault(expression_to_audit.date_scope, [])
            audit_or_domains.append(osv.expression.AND([
                expression_domain,
                groupby_domain,
            ]))

        domain = osv.expression.OR([
            osv.expression.AND([
                osv.expression.OR(audit_or_domain),
                self._get_options_domain(column_group_options, date_scope)
            ])
            for date_scope, audit_or_domain in audit_or_domains_per_date_scope.items()
        ])
        return domain

    def _get_expression_audit_aml_domain(self, expression_to_audit, options):
        """ Returns the domain used to audit a single provided expression.

        'account_codes' engine's D and C formulas can't be handled by a domain: we make the choice to display
        everything for them (so, audit shows all the lines that are considered by the formula). To avoid confusion from the user
        when auditing such lines, a default group by account can be used in the tree view.
        """
        if expression_to_audit.engine == 'account_codes':
            formula = expression_to_audit.formula.replace(' ', '')

            account_codes_domains = []
            for token in ACCOUNT_CODES_ENGINE_SPLIT_REGEX.split(formula.replace(' ', '')):
                if token:
                    match_dict = ACCOUNT_CODES_ENGINE_TERM_REGEX.match(token).groupdict()
                    account_codes_domain = [('account_id.code', '=like', f"{match_dict['prefix']}%")]

                    excluded_prefix_str = match_dict['excluded_prefixes']
                    if excluded_prefix_str:
                        for excluded_prefix in excluded_prefix_str.split(','):
                            # "'not like', prefix%" doesn't work
                            account_codes_domain += ['!', ('account_id.code', '=like', f"{excluded_prefix}%")]

                    account_codes_domains.append(account_codes_domain)

            return osv.expression.OR(account_codes_domains)

        if expression_to_audit.engine == 'tax_tags':
            tags = self.env['account.account.tag']._get_tax_tags(expression_to_audit.formula, self.env.company.account_fiscal_country_id.id)
            return [('tax_tag_ids', 'in', tags.ids)]

        if expression_to_audit.engine == 'domain':
            return ast.literal_eval(expression_to_audit.formula)

        return None

    @api.model
    def open_journal_items(self, options, params):
        ''' Open the journal items view with the proper filters and groups '''
        record_model, record_id = self._get_model_info_from_id(params.get('line_id'))
        view_id = self.env.ref(params['view_ref']).id if params.get('view_ref') else None

        ctx = {
            'search_default_group_by_account': 1,
            'search_default_posted': 0 if options.get('all_entries') else 1,
            'search_default_date_between': 1,
            'date_from': options.get('date').get('date_from'),
            'date_to': options.get('date').get('date_to'),
            'search_default_journal_id': params.get('journal_id', False),
            'expand': 1,
        }

        journal_type = params.get('journal_type')
        if journal_type:
            type_to_view_param = {
                'bank': {
                    'filter': 'search_default_bank',
                    'view_id': self.env.ref('account.view_move_line_tree_grouped_bank_cash').id
                },
                'cash': {
                    'filter': 'search_default_cash',
                    'view_id': self.env.ref('account.view_move_line_tree_grouped_bank_cash').id
                },
                'general': {
                    'filter': 'search_default_misc_filter',
                    'view_id': self.env.ref('account.view_move_line_tree_grouped_misc').id
                },
                'sale': {
                    'filter': 'search_default_sales',
                    'view_id': self.env.ref('account.view_move_line_tree_grouped_sales_purchases').id
                },
                'purchase': {
                    'filter': 'search_default_purchases',
                    'view_id': self.env.ref('account.view_move_line_tree_grouped_sales_purchases').id
                },
            }
            ctx.update({
                type_to_view_param[journal_type]['filter']: 1,
            })
            view_id = type_to_view_param[journal_type]['view_id']

        model_default_filters = {
            'account.account': 'search_default_account_id',
            'res.partner': 'search_default_partner_id',
            'account.journal': 'search_default_journal_id',
        }
        model_filter = model_default_filters.get(record_model)
        if model_filter:
            ctx.update({
                'active_id': record_id,
                model_filter: [record_id],
            })

        if options:
            for account_type in options.get('account_type', []):
                ctx.update({
                    f"search_default_{account_type['id']}": account_type['selected'] and 1 or 0,
                })

            if options.get('journals') and 'search_default_journal_id' not in ctx:
                selected_journals = [journal['id'] for journal in options['journals'] if journal.get('selected')]
                if len(selected_journals) == 1:
                    ctx['search_default_journal_id'] = selected_journals

            if options.get('analytic_accounts'):
                analytic_ids = [int(r) for r in options['analytic_accounts']]
                ctx.update({
                    'search_default_analytic_accounts': 1,
                    'analytic_ids': analytic_ids,
                })

        return {
            'name': self._get_action_name(params, record_model, record_id),
            'view_mode': 'tree,pivot,graph,kanban',
            'res_model': 'account.move.line',
            'views': [(view_id, 'list')],
            'type': 'ir.actions.act_window',
            'domain': [('display_type', 'not in', ('line_section', 'line_note'))],
            'context': ctx,
        }

    def open_unposted_moves(self, options, params=None):
        ''' Open the list of draft journal entries that might impact the reporting'''
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action = clean_action(action, env=self.env)
        action['domain'] = [('state', '=', 'draft'), ('date', '<=', options['date']['date_to'])]
        #overwrite the context to avoid default filtering on 'misc' journals
        action['context'] = {}
        return action

    def action_partner_reconcile(self, options, params):
        model, model_id = self._get_model_info_from_id(params['line_id'])

        if model != 'res.partner':
            raise UserError(_("Can't open partner reconciliation for line id %s ; model should res.partner.", params['line_id']))

        form = self.env.ref('account_accountant.action_manual_reconciliation').sudo()
        return {
            'type': 'ir.actions.client',
            'view_id': form.id,
            'tag': form.tag,
            'context': {
                **self._context,
                'partner_ids': [model_id],
                'active_id': model_id,
                'all_entries': True,
            },
        }

    def action_modify_manual_value(self, options, column_group_key, new_value_str, target_expression_id, rounding, json_friendly_column_group_totals):
        """ Edit a manual value from the report, updating or creating the corresponding account.report.external.value object.

        :param options: The option dict the report is evaluated with.

        :param column_group_key: The string identifying the column group into which the change as manual value needs to be done.

        :param new_value_str: The new value to be set, as a string.

        :param rounding: The number of decimal digits to round with.

        :param json_friendly_column_group_totals: The expression totals by column group already computed for this report, in the format returned
                                                  by _get_json_friendly_column_group_totals. These will be used to reevaluate the report, recomputing
                                                  only the expressions depending on the newly-modified manual value, and keeping all the results
                                                  from the previous computations for the other ones.
        """
        self.ensure_one()

        if 'multi_company' in options:
            raise UserError(_("Editing a manual report line is not allowed when multiple companies are selected."))

        if options['fiscal_position'] == 'all' and options['available_vat_fiscal_positions']:
            raise UserError(_("Editing a manual report line is not allowed in multivat setup when displaying data from all fiscal positions."))

        target_column_group_options = self._get_column_group_options(options, column_group_key)
        expressions_to_recompute = self.line_ids.expression_ids.filtered(lambda x: x.engine in ('external', 'aggregation')) # Only those lines' values can be impacted

        # Create the manual value
        target_expression = self.env['account.report.expression'].browse(target_expression_id)
        date_from, date_to, dummy = self._get_date_bounds_info(target_column_group_options, target_expression.date_scope)
        fiscal_position_id = target_column_group_options['fiscal_position'] if isinstance(target_column_group_options['fiscal_position'], int) else False

        external_values_domain = [
            ('target_report_expression_id', '=', target_expression.id),
            ('company_id', '=', self.env.company.id),
            ('foreign_vat_fiscal_position_id', '=', fiscal_position_id),
        ]

        if target_expression.formula == 'most_recent':
            value_to_adjust = 0
            existing_value_to_modify = self.env['account.report.external.value'].search([
                *external_values_domain,
                ('date', '=', date_to),
            ])

            # There should be at most 1
            if len(existing_value_to_modify) > 1:
                raise UserError(_("Inconsistent data: more than one external value at the same date for a 'most_recent' external line."))
        else:
            existing_external_values = self.env['account.report.external.value'].search([
                *external_values_domain,
                ('date', '>=', date_from),
                ('date', '<=', date_to),
            ], order='date ASC')
            existing_value_to_modify = existing_external_values[-1] if existing_external_values and str(existing_external_values[-1].date) == date_to  else None
            value_to_adjust = sum(existing_external_values.filtered(lambda x: x != existing_value_to_modify).mapped('value'))

        value_to_set = float_round(float(new_value_str) - value_to_adjust, precision_digits=rounding)
        if existing_value_to_modify:
            existing_value_to_modify.value = value_to_set
            existing_value_to_modify.flush_recordset()
        else:
            self.env['account.report.external.value'].create({
                'name': _("Manual value"),
                'value': value_to_set,
                'date': date_to,
                'target_report_expression_id': target_expression.id,
                'company_id': self.env.company.id,
                'foreign_vat_fiscal_position_id': fiscal_position_id,
            })

        # We recompute values for each column group, not only the one we modified a value in; this is important in case some date_scope is used to
        # retrieve the manual value from a previous period.

        # json_friendly_column_group_totals contains ids instead of expressions (because it comes from js) ; we need to convert them back to records
        all_column_groups_expression_totals = {}
        for column_group_key, expression_totals in json_friendly_column_group_totals.items():

            all_column_groups_expression_totals[column_group_key] = {}
            for expr_id, expr_totals in expression_totals.items():
                expression = self.env['account.report.expression'].browse(int(expr_id))  # Should already be in cache, so acceptable
                if expression not in expressions_to_recompute:
                    all_column_groups_expression_totals[column_group_key][expression] = expr_totals

        recomputed_expression_totals = self._compute_expression_totals_for_each_column_group(
            expressions_to_recompute, options, forced_all_column_groups_expression_totals=all_column_groups_expression_totals)
        lines = self._get_lines(options, all_column_groups_expression_totals=all_column_groups_expression_totals)

        return {
            'new_main_html': self.get_html(options, lines),
            'new_report_column_groups_totals': self._get_json_friendly_column_group_totals(recomputed_expression_totals),
        }

    @api.model
    def _sort_lines(self, lines, options):
        ''' Sort report lines based on the 'order_column' key inside the options.
        The value of options['order_column'] is an integer, positive or negative, indicating on which column
        to sort and also if it must be an ascending sort (positive value) or a descending sort (negative value).
        Note that for this reason, its indexing is made starting at 1, not 0.
        If this key is missing or falsy, lines is returned directly.

        This method has some limitations:
        - The selected_column must have 'sortable' in its classes.
        - All lines are sorted expect those having the 'total' class.
        - This only works when each line has an unique id.
        - All lines inside the selected_column must have a 'no_format' value.

        Example:

        parent_line_1           balance=11
            child_line_1        balance=1
            child_line_2        balance=3
            child_line_3        balance=2
            child_line_4        balance=7
            child_line_5        balance=4
            child_line_6        (total line)
        parent_line_2           balance=10
            child_line_7        balance=5
            child_line_8        balance=6
            child_line_9        (total line)


        The resulting lines will be:

        parent_line_2           balance=10
            child_line_7        balance=5
            child_line_8        balance=6
            child_line_9        (total line)
        parent_line_1           balance=11
            child_line_1        balance=1
            child_line_3        balance=2
            child_line_2        balance=3
            child_line_5        balance=4
            child_line_4        balance=7
            child_line_6        (total line)

        :param lines:   The report lines.
        :param options: The report options.
        :return:        Lines sorted by the selected column.
        '''
        def needs_to_be_at_bottom(line_elem):
            return self._parse_line_id(line_elem.get('id'))[-1][0] in ('total', 'load_more')

        def compare_values(a_line_dict, b_line_dict):
            type_seq = {
                type(None): 0,
                bool: 1,
                float: 2,
                int: 2,
                str: 3,
                datetime.date: 4,
                datetime.datetime: 5,
            }
            a_total = needs_to_be_at_bottom(a_line_dict)
            b_total = needs_to_be_at_bottom(b_line_dict)
            if a_total:
                if b_total:  # a_total & b_total
                    return 0
                else:    # a_total & !b_total
                    return -1 if descending else 1
            if b_total:  # => !a_total & b_total
                return 1 if descending else -1

            a_val = a_line_dict['columns'][column_index].get('no_format')
            b_val = b_line_dict['columns'][column_index].get('no_format')
            type_a, type_b = type_seq[type(a_val)], type_seq[type(b_val)]
            if type_a == type_b:
                return 0 if a_val == b_val else 1 if a_val > b_val else -1
            else:
                return type_a - type_b

        def merge_tree(tree_elem, ls):
            nonlocal descending  # The direction of the sort is needed to compare total lines
            ls.append(tree_elem)
            for tree_subelem in sorted(tree[tree_elem['id']], key=comp_key, reverse=descending):
                merge_tree(tree_subelem, ls)

        descending = options['order_column'] < 0 # To keep total lines at the end, used in compare_values & merge_tree scopes
        column_index = abs(options['order_column']) - 1 # To know from which column to sort, used in merge_tree scope

        comp_key = cmp_to_key(compare_values)
        sorted_list = []
        tree = defaultdict(list)
        for line in lines:
            tree[line.get('parent_id') or None].append(line)

        if None not in tree and len(tree) == 1:
            # Happens when unfolding a groupby line, to sort its children.
            sorting_root = list(tree.keys())[0]
        else:
            sorting_root = None

        for line in sorted(tree[sorting_root], key=comp_key, reverse=descending):
            merge_tree(line, sorted_list)
        return sorted_list

    def get_report_informations(self, previous_options):
        """
        return a dictionary of information that will be consumed by the js widget, manager_id, footnotes, html of report and searchview, ...
        """
        self.ensure_one()

        if not previous_options:
            previous_options = {}

        options = self._get_options(previous_options)

        if not self.root_report_id:
            # This report has no root, so it IS a root. We might want to load a variant instead.

            if options['report_id'] != self.id:
                # Load the variant instead of the root report
                return self.env['account.report'].browse(options['report_id']).get_report_informations({**previous_options, 'report_id': options['report_id']})

        searchview_dict = {'options': options, 'context': self.env.context, 'report': self}

        # Check whether there are unposted entries for the selected period or not (if the report allows it)
        if options.get('date') and options.get('all_entries') is not None:
            date_to = options['date'].get('date_to') or options['date'].get('date') or fields.Date.today()
            period_domain = [('state', '=', 'draft'), ('date', '<=', date_to)]
            options['unposted_in_period'] = bool(self.env['account.move'].search_count(period_domain))

        all_column_groups_expression_totals = self._compute_expression_totals_for_each_column_group(self.line_ids.expression_ids, options)
        lines = self._get_lines(options, all_column_groups_expression_totals)

        report_html = self.get_html(options, lines)

        # Convert all_column_groups_expression_totals to a json-friendly form (its keys are records)
        json_friendly_column_group_totals = self._get_json_friendly_column_group_totals(all_column_groups_expression_totals)

        report_manager = self._get_report_manager(options)
        info = {
            'options': options,
            'column_groups_totals': json_friendly_column_group_totals,
            'context': self.env.context,
            'report_manager_id': report_manager.id,
            'footnotes': [{'id': f.id, 'line': f.line, 'text': f.text} for f in report_manager.footnotes_ids],
            'main_html': report_html,
            'searchview_html': self.env['ir.ui.view']._render_template(self.search_template, values=searchview_dict),
        }

        return info

    def _get_json_friendly_column_group_totals(self, all_column_groups_expression_totals):
        # Convert all_column_groups_expression_totals to a json-friendly form (its keys are records)
        json_friendly_column_group_totals = {}
        for column_group_key, expressions_totals in all_column_groups_expression_totals.items():
            json_friendly_column_group_totals[column_group_key] = {expression.id: totals for expression, totals in expressions_totals.items()}
        return json_friendly_column_group_totals

    def _is_available_for(self, options):
        """ Called on report variants to know whether they are available for the provided options or not, computed for their root report,
        computing their availability_condition field.

        Note that only the options initialized by the init_options with a more prioritary sequence than _init_options_variants are guaranteed to
        be in the provided options' dict (since this function is called by _init_options_variants, while resolving a call to _get_options()).
        """
        self.ensure_one()

        if options.get('multi_company'):
            companies = self.env['res.company'].browse([comp['id'] for comp in options['multi_company']])
        else:
            companies = self.env.company

        if self.availability_condition == 'country':
            countries = companies.account_fiscal_country_id
            if self.filter_fiscal_position:
                foreign_vat_fpos = self.env['account.fiscal.position'].search([
                    ('foreign_vat', '!=', False),
                    ('company_id', 'in', companies.ids),
                ])
                countries += foreign_vat_fpos.country_id

            return not self.country_id or self.country_id in countries

        elif self.availability_condition == 'coa':
            # When restricting to 'coa', the report is only available is all the companies have the same CoA as the report
            return self.chart_template_id == companies.chart_template_id

        return True

    def _get_html_render_values(self, options, report_manager):
        return {
            'report': self,
            'report_summary': report_manager.summary,
            'report_company_name': self.env.company.name,
            'options': options,
            'context': self.env.context,
            'model': self,
            'table_start': markupsafe.Markup('<tbody>'),
            'table_end': markupsafe.Markup('''
                </tbody></table>
                <div style="page-break-after: always"></div>
                <table class="o_account_reports_table table-hover">
            '''),
            'column_headers_render_data': self._get_column_headers_render_data(options),
        }

    def _get_column_headers_render_data(self, options):
        column_headers_render_data = {}

        # We only want to consider the columns that are visible in the current report and don't rely on self.column_ids
        # since custom reports could alter them (e.g. for multi-currency purposes)
        columns = [col for col in options['columns'] if col['column_group_key'] == next(k for k in options['column_groups'])]

        # Compute the colspan of each header level, aka the number of single columns it contains at the base ot the hierarchy
        level_colspan_list = column_headers_render_data['level_colspan'] = []
        for i in range(len(options['column_headers'])):
            colspan = max(len(columns), 1)
            for column_header in options['column_headers'][i + 1:]:
                colspan *= len(column_header)
            level_colspan_list.append(colspan)

        # Compute the number of times each header level will have to be repeated, and its colspan to properly handle horizontal groups/comparisons
        column_headers_render_data['level_repetitions'] = []
        for i in range(len(options['column_headers'])):
            colspan = 1
            for column_header in options['column_headers'][:i]:
                colspan *= len(column_header)
            column_headers_render_data['level_repetitions'].append(colspan)

        # Custom reports have the possibility to define custom subheaders that will be displayed between the generic header and the column names.
        column_headers_render_data['custom_subheaders'] = options.get('custom_columns_subheaders', []) * len(options['column_groups'])

        return column_headers_render_data

    def _get_action_name(self, params, record_model=None, record_id=None):
        if not (record_model or record_id):
            record_model, record_id = self._get_model_info_from_id(params.get('line_id'))
        return params.get('name') or self.env[record_model].browse(record_id).display_name or ''

    def _format_lines_for_display(self, lines, options):
        """
        This method should be overridden in a report in order to apply specific formatting when printing
        the report lines.

        Used for example by the carryover functionnality in the generic tax report.
        :param lines: A list with the lines for this report.
        :param options: The options for this report.
        :return: The formatted list of lines
        """
        return lines

    def _format_lines_for_ellipsis(self, lines, options):
        '''
        This method allows to adjust the size of the line leading column (usually name) by adjusting its colspan
        value. The main idea is that we look for the next column with a value and we make the name take all the space
        available until there.

        +------------------+-------+-------+-------+              +------------------+-------+-------+-------+
        | Name (colspan=1) |       |       | Value |      =>      | Name (colspan=3)                 | Value |
        +------------------+-------+-------+-------+              +------------------+-------+-------+-------+

        We take into account the level of the line and if the line has children or is a children. That helps
        keep the report coherent and easy to read.

        Note 1: The goal of the key is to adjust the values of the colspan by level and by hierarchy
        (i.e. if the line is a root line or a children line). That helps keeping the report coherent and easy to read.
        '''
        if len(options['columns']) > 1:
            max_colspan_by_level = {}

            for line in lines:
                # See Note 1
                key = f"{line.get('level')}_{'child' if 'parent_id' in line else 'root'}"

                # We look for the first column with a name value
                for index, column in enumerate(line.get('columns'), start=1):
                    if (column.get('name') or column.get('info_popup_data') or column.get('edit_popup_data')) \
                       and (index) < max_colspan_by_level.get(key, math.inf):
                        max_colspan_by_level[key] = index

                        # No need to keep checking columns after this
                        break

            # Apply colspans
            for line in lines:
                new_columns = []
                # See Note 1
                key = f"{line.get('level')}_{'child' if 'parent_id' in line else 'root'}"
                max_colspan = max_colspan_by_level.get(key)

                if max_colspan is not None:
                    # We remove empty leading columns
                    for index, column in enumerate(line.get('columns'), start=1):
                        if index >= max_colspan:
                            new_columns.append(column)

                    line['columns'] = new_columns
                    line['colspan'] = max_colspan or line.get('colspan', 1)
                else:
                    line['colspan'] = len(line['columns']) + 1
                    line['columns'] = []

        return lines

    def get_html(self, options, lines, additional_context=None, template=None):
        template = self.main_template if template is None else template
        report_manager = self._get_report_manager(options)

        render_values = self._get_html_render_values(options, report_manager)
        if additional_context:
            render_values.update(additional_context)

        if options.get('order_column'):
            lines = self._sort_lines(lines, options)

        lines = self._format_lines_for_display(lines, options)
        lines = self._format_lines_for_ellipsis(lines, options)

        # Catch negative numbers when present
        for line in lines:
            for col in line['columns']:
                if (
                    isinstance(col.get('no_format'), float)
                    and float_compare(col['no_format'], 0.0, precision_digits=self.env.company.currency_id.decimal_places) == -1
                ):
                    col['class'] = (col.get('class') and ' ' or '') + 'number color-red'

        render_values['lines'] = lines

        # Manage footnotes.
        footnotes_to_render = []
        if self.env.context.get('print_mode', False):
            # we are in print mode, so compute footnote number and include them in lines values, otherwise, let the js compute the number correctly as
            # we don't know all the visible lines.
            footnotes = dict([(str(f.line), f) for f in report_manager.footnotes_ids])
            number = 0
            for line in lines:
                f = footnotes.get(str(line.get('id')))
                if f:
                    number += 1
                    line['footnote'] = str(number)
                    footnotes_to_render.append({'id': f.id, 'number': number, 'text': f.text})

        # Render.
        html = self.env['ir.qweb']._render(template, render_values)
        if self.env.context.get('print_mode', False):
            for k,v in self._replace_class().items():
                html = html.replace(k, v)
            # append footnote as well
            html = html.replace(markupsafe.Markup('<div class="js_account_report_footnotes"></div>'), self.get_html_footnotes(footnotes_to_render))
        return html

    def get_expanded_line_html(self, options, line_dict_id, groupby, expand_function_name, progress, offset):
        """ Returns the html to be injected into the report when unfolding a line with an expand_function for the first time.
        """
        lines = self._expand_unfoldable_line(expand_function_name, line_dict_id, groupby, options, progress, offset)
        lines = self._fully_unfold_lines_if_needed(lines, options)
        return self.get_html(options, lines, template=self.line_template)

    def _expand_unfoldable_line(self, expand_function_name, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        if not expand_function_name:
            raise UserError(_("Trying to expand a line without an expansion function."))

        if not progress:
            progress = {column_group_key: 0 for column_group_key in options['column_groups']}

        expand_function = self._get_custom_report_function(expand_function_name, 'expand_unfoldable_line')
        expansion_result = expand_function(line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=unfold_all_batch_data)

        rslt = expansion_result['lines']
        if expansion_result.get('has_more'):
            # We only add load_more line for groupby
            next_offset = offset + expansion_result['offset_increment']
            rslt.append(self._get_load_more_line(next_offset, line_dict_id, expand_function_name, groupby, expansion_result.get('progress', 0), options))

        # In some specific cases, we may want to add lines that are always at the end. So they need to be added after the load more line.
        if expansion_result.get('after_load_more_lines'):
            rslt.extend(expansion_result['after_load_more_lines'])

        return rslt

    @api.model
    def _get_load_more_line(self, offset, parent_line_id, expand_function_name, groupby, progress, options):
        """ Returns a 'Load more' line allowing to reach the subsequent elements of an unfolded line with an expand function if the maximum
        limit of sublines is reached (we load them by batch, using the load_more_limit field's value).

        :param offset: The offset to be passed to the expand function to generate the next results, when clicking on this 'load more' line.

        :param parent_line_id: The generic id of the line this load more line is created for.

        :param expand_function_name: The name of the expand function this load_more is created for (so, the one of its parent).

        :param progress: A json-formatted dict(column_group_key, value) containing the progress value for each column group, as it was
                         returned by the expand function. This is for example used by reports such as the general ledger, whose lines display a c
                         cumulative sum of their balance and the one of all the previous lines under the same parent. In this case, progress
                         will be the total sum of all the previous lines before the load_more line, that the subsequent lines will need to use as
                         base for their own cumulative sum.

        :param options: The options dict corresponding to this report's state.
        """
        return {
            'id': self._get_generic_line_id(None, None, parent_line_id=parent_line_id, markup='load_more'),
            'name': _("Load more..."),
            'class': 'o_account_reports_load_more text-center',
            'parent_id': parent_line_id,
            'expand_function': expand_function_name,
            'columns': [{} for col in options['columns']],
            'unfoldable': False,
            'unfolded': False,
            'offset': offset,
            'groupby': groupby, # We keep the groupby value from the parent, so that it can be propagated through js
            'progress': progress,
        }

    def _report_expand_unfoldable_line_with_groupby(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        # The line we're expanding might be an inner groupby; we first need to find the report line generating it
        report_line_id = None
        for dummy, model, model_id in reversed(self._parse_line_id(line_dict_id)):
            if model == 'account.report.line':
                report_line_id = model_id
                break

        if report_line_id is None:
            raise UserError(_("Trying to expand a group for a line which was not generated by a report line: %s", line_dict_id))

        line = self.env['account.report.line'].browse(report_line_id)

        if ',' not in groupby and not self._context.get('print_mode'):
            # if ',' not in groupby, then its a terminal groupby (like 'id' in 'partner_id, id'), so we can use the 'load more' feature if necessary
            # When printing, we want to ignore the limit.
            limit_to_load = self.load_more_limit + 1 if self.load_more_limit else None
        else:
            # Else, we disable it
            limit_to_load = None
            offset = 0

        rslt_lines = line._expand_groupby(line_dict_id, groupby, options, offset=offset, limit=limit_to_load)
        lines_to_load = rslt_lines[:self.load_more_limit] if limit_to_load else rslt_lines

        return {
            'lines': lines_to_load,
            'offset_increment': len(lines_to_load),
            'has_more': len(lines_to_load) < len(rslt_lines),
        }

    def get_html_footnotes(self, footnotes):
        rcontext = {'footnotes': footnotes, 'context': self.env.context}
        html = self.env['ir.ui.view']._render_template(self.footnotes_template, values=rcontext)
        return html

    def _get_report_manager(self, options):
        domain = [('report_name', '=', self._name)]
        domain = (domain + [('report_id', '=', self.id)]) if 'id' in dir(self) else domain
        multi_company_report = options.get('multi_company', False)
        if not multi_company_report:
            domain += [('company_id', '=', self.env.company.id)]
        else:
            domain += [('company_id', '=', False)]
        existing_manager = self.env['account.report.manager'].search(domain, limit=1)
        if not existing_manager:
            existing_manager = self.env['account.report.manager'].create({
                'report_name': self._name,
                'company_id': self.env.company.id if not multi_company_report else False,
                'report_id': self.id if 'id' in dir(self) else False,
            })
        return existing_manager

    @api.model
    def format_value(self, value, currency=False, blank_if_zero=True, figure_type=None, digits=1):
        """ Formats a value for display in a report (not especially numerical). figure_type provides the type of formatting we want.
        """
        if figure_type == 'none':
            return value

        if value is None:
            return ''

        if figure_type == 'monetary':
            currency = currency or self.env.company.currency_id
            digits = None
        elif figure_type in ('date', 'datetime'):
            return format_date(self.env, value)
        else:
            currency = None

        if self.is_zero(value, currency=currency, figure_type=figure_type, digits=digits):
            if blank_if_zero:
                return ''
            # don't print -0.0 in reports
            value = abs(value)

        if self._context.get('no_format'):
            return value

        formatted_amount = formatLang(self.env, value, currency_obj=currency, digits=digits)

        if figure_type == 'percentage':
            return f"{formatted_amount}%"

        return formatted_amount

    @api.model
    def is_zero(self, amount, currency=False, figure_type=None, digits=1):
        if figure_type == 'monetary':
            currency = currency or self.env.company.currency_id
            return currency.is_zero(amount)

        if figure_type == 'integer':
            digits = 0
        return float_is_zero(amount, precision_digits=digits)

    @api.model
    def _format_aml_name(self, line_name, move_ref, move_name=None):
        ''' Format the display of an account.move.line record. As its very costly to fetch the account.move.line
        records, only line_name, move_ref, move_name are passed as parameters to deal with sql-queries more easily.

        :param line_name:   The name of the account.move.line record.
        :param move_ref:    The reference of the account.move record.
        :param move_name:   The name of the account.move record.
        :return:            The formatted name of the account.move.line record.
        '''
        names = []
        if move_name is not None and move_name != '/':
            names.append(move_name)
        if move_ref and move_ref != '/':
            names.append(move_ref)
        if line_name and line_name != move_name and line_name != '/':
            names.append(line_name)
        name = '-'.join(names)
        return name

    def format_date(self, options, dt_filter='date'):
        date_from = fields.Date.from_string(options[dt_filter]['date_from'])
        date_to = fields.Date.from_string(options[dt_filter]['date_to'])
        return self._get_dates_period(date_from, date_to, options['date']['mode'])['string']

    def export_file(self, options, file_generator):
        self.ensure_one()
        return {
            'type': 'ir_actions_account_report_download',
            'data': {
                 'options': json.dumps(options),
                 'file_generator': file_generator,
             }
        }

    def _replace_class(self):
        """When printing pdf, we sometime want to remove/add/replace class for the report to look a bit different on paper
        this method is used for this, it will replace occurence of value key by the dict value in the generated pdf
        """
        return {
            'o_account_reports_no_print': '',
            'table-responsive': '',
        }

    def export_to_pdf(self, options):
        self.ensure_one()
        # As the assets are generated during the same transaction as the rendering of the
        # templates calling them, there is a scenario where the assets are unreachable: when
        # you make a request to read the assets while the transaction creating them is not done.
        # Indeed, when you make an asset request, the controller has to read the `ir.attachment`
        # table.
        # This scenario happens when you want to print a PDF report for the first time, as the
        # assets are not in cache and must be generated. To workaround this issue, we manually
        # commit the writes in the `ir.attachment` table. It is done thanks to a key in the context.
        if not config['test_enable']:
            self = self.with_context(commit_assetsbundle=True)

        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
        }

        print_mode_self = self.with_context(print_mode=True)
        body_html = print_mode_self.get_html(options, print_mode_self._get_lines(options))
        body = self.env['ir.ui.view']._render_template(
            "account_reports.print_template",
            values=dict(rcontext, body_html=body_html),
        )
        footer = self.env['ir.actions.report']._render_template("web.internal_layout", values=rcontext)
        footer = self.env['ir.actions.report']._render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=markupsafe.Markup(footer.decode())))

        landscape = False
        if len(options['columns']) * len(options['column_groups']) > 5:
            landscape = True

        file_content = self.env['ir.actions.report']._run_wkhtmltopdf(
            [body],
            footer=footer.decode(),
            landscape=landscape,
            specific_paperformat_args={
                'data-report-margin-top': 10,
                'data-report-header-spacing': 10
            }
        )

        return {
            'file_name': self.get_default_report_filename('pdf'),
            'file_content': file_content,
            'file_type': 'pdf',
        }

    def export_to_xlsx(self, options, response=None):
        def write_with_colspan(sheet, x, y, value, colspan, style):
            if colspan == 1:
                sheet.write(y, x, value, style)
            else:
                sheet.merge_range(y, x, y, x + colspan - 1, value, style)
        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        sheet = workbook.add_worksheet(self.name[:31])

        date_default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'num_format': 'yyyy-mm-dd'})
        date_default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'num_format': 'yyyy-mm-dd'})
        default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 6, 'font_color': '#666666'})
        level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 1, 'font_color': '#666666'})
        level_2_col1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_2_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_3_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        level_3_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_3_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})

        #Set the first column width to 50
        sheet.set_column(0, 0, 50)

        y_offset = 0
        x_offset = 1 # 1 and not 0 to leave space for the line name
        lines = self.with_context(no_format=True, print_mode=True, prefetch_fields=False)._get_lines(options)

        # Add headers.
        # For this, iterate in the same way as done in main_table_header template
        column_headers_render_data = self._get_column_headers_render_data(options)
        for header_level_index, header_level in enumerate(options['column_headers']):
            for header_to_render in header_level * column_headers_render_data['level_repetitions'][header_level_index]:
                colspan = header_to_render.get('colspan', column_headers_render_data['level_colspan'][header_level_index])
                write_with_colspan(sheet, x_offset, y_offset, header_to_render.get('name', ''), colspan, title_style)
                x_offset += colspan
            y_offset += 1
            x_offset = 1

        for subheader in column_headers_render_data['custom_subheaders']:
            colspan = subheader.get('colspan', 1)
            write_with_colspan(sheet, x_offset, y_offset, subheader.get('name', ''), colspan, title_style)
            x_offset += colspan
        y_offset += 1
        x_offset = 1

        for column in options['columns']:
            colspan = column.get('colspan', 1)
            write_with_colspan(sheet, x_offset, y_offset, column.get('name', ''), colspan, title_style)
            x_offset += colspan
        y_offset += 1

        if options.get('order_column'):
            lines = self._sort_lines(lines, options)

        # Add lines.
        for y in range(0, len(lines)):
            level = lines[y].get('level')
            if lines[y].get('caret_options'):
                style = level_3_style
                col1_style = level_3_col1_style
            elif level == 0:
                y_offset += 1
                style = level_0_style
                col1_style = style
            elif level == 1:
                style = level_1_style
                col1_style = style
            elif level == 2:
                style = level_2_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') and level_2_col1_total_style or level_2_col1_style
            elif level == 3:
                style = level_3_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') and level_3_col1_total_style or level_3_col1_style
            else:
                style = default_style
                col1_style = default_col1_style

            #write the first column, with a specific style to manage the indentation
            cell_type, cell_value = self._get_cell_type_value(lines[y])
            if cell_type == 'date':
                sheet.write_datetime(y + y_offset, 0, cell_value, date_default_col1_style)
            else:
                sheet.write(y + y_offset, 0, cell_value, col1_style)

            #write all the remaining cells
            for x in range(1, len(lines[y]['columns']) + 1):
                cell_type, cell_value = self._get_cell_type_value(lines[y]['columns'][x - 1])
                if cell_type == 'date':
                    sheet.write_datetime(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, date_default_style)
                else:
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, style)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return {
            'file_name': self.get_default_report_filename('xlsx'),
            'file_content': generated_file,
            'file_type': 'xlsx',
        }

    def _get_cell_type_value(self, cell):
        if 'date' not in cell.get('class', '') or not cell.get('name'):
            # cell is not a date
            return ('text', cell.get('name', ''))
        if isinstance(cell['name'], (float, datetime.date, datetime.datetime)):
            # the date is xlsx compatible
            return ('date', cell['name'])
        try:
            # the date is parsable to a xlsx compatible date
            lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
            return ('date', datetime.datetime.strptime(cell['name'], lg.date_format))
        except:
            # the date is not parsable thus is returned as text
            return ('text', cell['name'])

    def get_vat_for_export(self, options):
        """ Returns the VAT number to use when exporting this report with the provided
        options. If a single fiscal_position option is set, its VAT number will be
        used; else the current company's will be, raising an error if its empty.
        """
        self.ensure_one()

        if self.filter_multi_company == 'tax_units' and options['tax_unit'] != 'company_only':
            tax_unit = self.env['account.tax.unit'].browse(options['tax_unit'])
            return tax_unit.vat

        if options['fiscal_position'] in {'all', 'domestic'}:
            company = self.env.company
            if not company.vat:
                action = self.env.ref('base.action_res_company_form')
                raise RedirectWarning(_('No VAT number associated with your company. Please define one.'), action.id, _("Company Settings"))
            return company.vat

        fiscal_position = self.env['account.fiscal.position'].browse(options['fiscal_position'])
        return fiscal_position.foreign_vat

    @api.model
    def get_report_company_ids(self, options):
        """ Returns a list containing the ids of the companies to be used to
        render this report, following the provided options.
        """
        if options.get('multi_company'):
            return [comp_data['id'] for comp_data in options['multi_company']]
        else:
            return self.env.company.ids

    def _get_partner_and_general_ledger_initial_balance_line(self, options, parent_line_id, eval_dict, account_currency=None):
        """ Helper to generate dynamic 'initial balance' lines, used by general ledger and partner ledger.
        """
        line_columns = []
        for column in options['columns']:
            col_value = eval_dict[column['column_group_key']].get(column['expression_label'])
            col_expr_label = column['expression_label']

            if col_value is None or (col_expr_label == 'amount_currency' and not account_currency):
                line_columns.append({})
            else:
                if col_expr_label == 'amount_currency':
                    formatted_value = self.format_value(col_value, currency=account_currency, figure_type=column['figure_type'])
                else:
                    formatted_value = self.format_value(col_value, figure_type=column['figure_type'])

                line_columns.append({
                    'name': formatted_value,
                    'no_format': col_value,
                    'class': 'number',
                })

        if not any(column.get('no_format') for column in line_columns):
            return None

        return {
            'id': self._get_generic_line_id(None, None, parent_line_id=parent_line_id, markup='initial'),
            'class': 'o_account_reports_initial_balance',
            'name': _("Initial Balance"),
            'parent_id': parent_line_id,
            'columns': line_columns,
        }

    def _compute_growth_comparison_column(self, options, value1, value2, green_on_positive=True):
        ''' Helper to get the additional columns due to the growth comparison feature. When only one comparison is
        requested, an additional column is there to show the percentage of growth based on the compared period.
        :param options:             The report options.
        :param value1:              The value in the current period.
        :param value2:              The value in the compared period.
        :param green_on_positive:   A flag customizing the value with a green color depending if the growth is positive.
        :return:                    The new columns to add to line['columns'].
        '''
        if float_is_zero(value2, precision_rounding=0.1):
            return {'name': _('n/a'), 'class': 'number'}
        else:
            res = round((value1 - value2) / value2 * 100, 1)

            # In case the comparison is made on a negative figure, the color should be the other
            # way around. For example:
            #                       2018         2017           %
            # Product Sales      1000.00     -1000.00     -200.0%
            #
            # The percentage is negative, which is mathematically correct, but my sales increased
            # => it should be green, not red!
            if float_is_zero(res, precision_rounding=0.1):
                return {'name': '0.0%', 'class': 'number'}
            elif (res > 0) != (green_on_positive and value2 > 0):
                return {'name': str(res) + '%', 'class': 'number color-red'}
            else:
                return {'name': str(res) + '%', 'class': 'number color-green'}

    def _display_growth_comparison(self, options):
        ''' Helper determining if the growth comparison feature should be displayed or not.
        :param options: The report options.
        :return:        A boolean.
        '''
        return self.filter_growth_comparison \
               and options.get('comparison') \
               and len(options['comparison'].get('periods', [])) == 1 \
               and options['selected_horizontal_group_id'] is None \
               and len(options['columns']) == 2

    @api.model
    def _check_groupby_fields(self, groupby_fields_name):
        """ Checks that each string in the groupby_fields_name list is a valid groupby value for an accounting report (so: it must be a field from
        account.move.line).
        """
        for field_name in groupby_fields_name:
            groupby_field = self.env['account.move.line']._fields.get(field_name)
            if not groupby_field:
                raise UserError(_("Field %s does not exist on account.move.line.", field_name))
            if not groupby_field.store:
                raise UserError(_("Field %s of account.move.line is not stored, and hence cannot be used in a groupby expression", field_name))

    # ============ Accounts Coverage Debugging Tool - START ================
    def action_download_xlsx_accounts_coverage_report(self):
        """
        Generate an XLSX file that can be used to debug the
        report by issuing the following warnings if applicable:
        - an account exists in the Chart of Accounts but is not mentioned in any line of the report (red)
        - an account is reported in multiple lines of the report (orange)
        - an account is reported in a line of the report but does not exist in the Chart of Accounts (yellow)
        """
        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet(_('Accounts coverage'))
        worksheet.set_column(0, 0, 15)
        worksheet.set_column(1, 1, 75)
        worksheet.set_column(2, 2, 80)
        worksheet.freeze_panes(1, 0)

        headers = [_("Account Code"), _("Error message"), _("Report lines mentioning the account code"), '#FFFFFF']
        lines = [headers] + self._generate_accounts_coverage_report_xlsx_lines()
        for i, line in enumerate(lines):
            worksheet.write_row(i, 0, line[:-1], workbook.add_format({'bg_color': line[-1]}))

        workbook.close()
        attachment_id = self.env['ir.attachment'].create({
            'name': f"{self.display_name} - {_('Accounts Coverage Report')}",
            'datas': base64.encodebytes(output.getvalue())
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment_id.id}",
            "target": "self",
        }

    def _generate_accounts_coverage_report_xlsx_lines(self):
        """
        Generate the lines of the XLSX file that can be used to debug the
        report by issuing the following warnings if applicable:
        - an account exists in the Chart of Accounts but is not mentioned in any line of the report (red)
        - an account is reported in multiple lines of the report (orange)
        - an account is reported in a line of the report but does not exist in the Chart of Accounts (yellow)
        """
        self.ensure_one()

        if self.env.company.account_fiscal_country_id != self.country_id:
            raise UserError(_("The company's country does not match the report's country."))

        all_reported_accounts = self.env["account.account"]  # All accounts mentioned in the report (including those reported without using the account code)
        accounts_by_expressions = {}    # {expression_id: account.account objects}
        reported_account_codes = []     # [{'prefix': ..., 'balance': ..., 'exclude': ..., 'line': ...}, ...]
        non_reported_codes = set()      # codes that exist in the CoA but are not reported in the report
        non_existing_codes = defaultdict(lambda: self.env["account.report.line"])  # {non_existing_account_code: {lines_with_that_code,}}
        candidate_duplicate_codes = defaultdict(lambda: self.env["account.report.line"])  # {candidate_duplicate_account_code: {lines_with_that_code,}}
        duplicate_codes = defaultdict(lambda: self.env["account.report.line"])  # {verified duplicate_account_code: {lines_with_that_code,}}
        common_account_domain = [('company_id', '=', self.env.company.id), ('deprecated', '=', False)]

        expressions = self.line_ids.expression_ids._expand_aggregations()
        for i, expr in enumerate(expressions):
            reported_accounts = self.env["account.account"]
            if expr.engine == "domain":
                domain = literal_eval(expr.formula.strip())
                for j, operand in enumerate(domain):
                    if isinstance(operand, tuple):
                        operand = list(operand)
                        if not operand[0].startswith('account_id.'):
                            continue
                        operand[0] = operand[0].replace('account_id.', '')
                        # Check that the code exists in the CoA
                        if operand[0] == 'code' and not self.env["account.account"].search([operand]):
                            non_existing_codes[operand[2]] |= expr.report_line_id
                    domain[j] = operand
                reported_accounts = self.env['account.account'].search(domain)
            elif expr.engine == "account_codes":
                account_codes = []
                for token in ACCOUNT_CODES_ENGINE_SPLIT_REGEX.split(expr.formula.replace(' ', '')):
                    if not token:
                        continue
                    token_match = ACCOUNT_CODES_ENGINE_TERM_REGEX.match(token)
                    if not token_match:
                        continue
                    parsed_token = token_match.groupdict()
                    account_codes.append({
                        'prefix': parsed_token['prefix'],
                        'balance': parsed_token['balance_character'],
                        'exclude': parsed_token['excluded_prefixes'].split(',') if parsed_token['excluded_prefixes'] else [],
                        'line': expr.report_line_id,
                    })
                for account_code in account_codes:
                    reported_account_codes.append(account_code)
                    reported_accounts |= self.env["account.account"].search([
                        *common_account_domain,
                        ("code", "=like", account_code['prefix'] + "%"),
                        *[("code", "not like", excl) for excl in account_code['exclude']],
                    ])
                    # Check that the code exists in the CoA
                    if not self.env["account.account"].search([
                        *common_account_domain,
                        ('code', '=like', account_code['prefix'] + '%')
                    ]):
                        non_existing_codes[account_code['prefix']] |= account_code['line']
                    for account_code_exclude in account_code['exclude']:
                        if not self.env["account.account"].search([
                            *common_account_domain,
                            ('code', '=like', account_code_exclude + '%')
                        ]):
                            non_existing_codes[account_code_exclude] |= account_code['line']
            all_reported_accounts |= reported_accounts
            accounts_by_expressions[expr.id] = reported_accounts

            # Check if the account is reported in multiple lines of the report
            for expr2 in expressions[:i + 1]:
                reported_accounts2 = accounts_by_expressions[expr2.id]
                for duplicate_account in (reported_accounts & reported_accounts2):
                    if len(expr.report_line_id | expr2.report_line_id) > 1:
                        candidate_duplicate_codes[duplicate_account.code] |= expr.report_line_id | expr2.report_line_id

        # Check that the duplicates are not false positives because of the balance character
        for candidate_duplicate_code, candidate_duplicate_lines in candidate_duplicate_codes.items():
            seen_balance_chars = []
            for reported_account_code in reported_account_codes:
                if candidate_duplicate_code.startswith(reported_account_code['prefix']) and reported_account_code['balance']:
                    seen_balance_chars.append(reported_account_code['balance'])
            if not seen_balance_chars or seen_balance_chars.count("C") > 1 or seen_balance_chars.count("D") > 1:
                duplicate_codes[candidate_duplicate_code] |= candidate_duplicate_lines

        # Check that all codes in CoA are correctly reported
        accounts_in_coa = []
        if self.root_report_id and self.root_report_id == self.env.ref('account_reports.profit_and_loss'):
            accounts_in_coa = self.env["account.account"].search([
                *common_account_domain,
                ('account_type', 'in', ("income", "income_other", "expense", "expense_depreciation", "expense_direct_cost")),
                ('account_type', '!=', "off_balance"),
            ])
        elif self.root_report_id and self.root_report_id == self.env.ref('account_reports.balance_sheet'):
            accounts_in_coa = self.env["account.account"].search([
                *common_account_domain,
                ('account_type', 'not in', ("off_balance", "income", "income_other", "expense", "expense_depreciation", "expense_direct_cost"))
            ])
        else:
            accounts_in_coa = self.env["account.account"].search([common_account_domain])
        for account_in_coa in accounts_in_coa:
            if account_in_coa not in all_reported_accounts:
                non_reported_codes.add(account_in_coa.code)

        # Create the lines that will be displayed in the xlsx
        all_reported_codes = sorted(set(all_reported_accounts.mapped("code")) | non_reported_codes | non_existing_codes.keys())
        errors_trie = self._get_accounts_coverage_report_errors_trie(all_reported_codes, non_reported_codes, duplicate_codes, non_existing_codes)
        errors_trie = self._regroup_accounts_coverage_report_errors_trie(errors_trie)
        return self._get_accounts_coverage_report_coverage_lines("", errors_trie)

    def _get_accounts_coverage_report_errors_trie(self, all_reported_codes, non_reported_codes, duplicate_codes, non_existing_codes):
        """
        Create the trie that will be used to regroup the same errors on the same subcodes.
        This trie will be in the form of:
        {
            "children": {
                "1": {
                    "children": {
                        "10": { ... },
                        "11": { ... },
                    },
                    "lines": {
                        "Line1",
                        "Line2",
                    },
                    "errors": {
                        "DUPLICATE"
                    }
                },
            "lines": {
                "",
            },
            "errors": {
                None    # Avoid that all codes are merged into the root with the code "" in case all of the errors are the same
            },
        }
        """
        errors_trie = {"children": {}, "lines": {}, "errors": {None}}
        for reported_code in all_reported_codes:
            current_trie = errors_trie
            lines = self.env["account.report.line"]
            errors = set()
            if reported_code in non_reported_codes:
                errors.add("NON_REPORTED")
            elif reported_code in duplicate_codes:
                lines |= duplicate_codes[reported_code]
                errors.add("DUPLICATE")
            elif reported_code in non_existing_codes:
                lines |= non_existing_codes[reported_code]
                errors.add("NON_EXISTING")
            for j in range(1, len(reported_code) + 1):
                current_trie = current_trie["children"].setdefault(reported_code[:j], {
                    "children": {},
                    "lines": lines,
                    "errors": errors
                })
        return errors_trie

    def _regroup_accounts_coverage_report_errors_trie(self, trie):
        """
        Regroup the codes that have the same error under the same common subcode/prefix.
        This is done in-place on the given trie.
        """
        if trie.get("children"):
            children_errors = set()
            children_lines = self.env["account.report.line"]
            if trie.get("errors"):  # Add own error
                children_errors |= set(trie.get("errors"))
            for child in trie["children"].values():
                regroup = self._regroup_accounts_coverage_report_errors_trie(child)
                children_lines |= regroup["lines"]
                children_errors |= set(regroup["errors"])
            if len(children_errors) == 1 and children_lines and children_lines == trie["lines"]:
                trie["children"] = {}
                trie["lines"] = children_lines
                trie["errors"] = children_errors
        return trie

    def _get_accounts_coverage_report_coverage_lines(self, subcode, trie, coverage_lines=None):
        """
        Create the coverage lines from the grouped trie. Each line has
        - the account code
        - the error message
        - the lines on which the account code is used
        - the color of the error message for the xlsx
        """
        # Dictionnary of the three possible errors, their message and the corresponding color for the xlsx file
        ERRORS = {
            "NON_REPORTED": {
                "msg": _("This account exists in the Chart of Accounts but is not mentioned in any line of the report"),
                "color": "#FF0000"
            },
            "DUPLICATE": {
                "msg": _("This account is reported in multiple lines of the report"),
                "color": "#FF8916"
            },
            "NON_EXISTING": {
                "msg": _("This account is reported in a line of the report but does not exist in the Chart of Accounts"),
                "color": "#FFBF00"
            },
        }
        if coverage_lines is None:
            coverage_lines = []
        if trie.get("children"):
            for child in trie.get("children"):
                self._get_accounts_coverage_report_coverage_lines(child, trie["children"][child], coverage_lines)
        else:
            error = list(trie["errors"])[0] if trie["errors"] else False
            if error:
                coverage_lines.append([
                    subcode,
                    ERRORS[error]["msg"],
                    " + ".join(trie["lines"].sorted().mapped("name")),
                    ERRORS[error]["color"]
                ])
        return coverage_lines

    # ============ Accounts Coverage Debugging Tool - END ================


class AccountReportLine(models.Model):
    _inherit = 'account.report.line'

    def _expand_groupby(self, line_dict_id, groupby, options, offset=0, limit=None):
        """ Expand function used to get the sublines of a groupby.
        groupby param is a string consisting of one or more coma-separated field names. Only the first one
        will be used for the expansion; if there are subsequent ones, the generated lines will themselves used them as
        their groupby value, and point to this expand_function, hence generating a hierarchy of groupby).
        """
        self.ensure_one()

        # If this line is a sub-groupby of groupby line (for example, when grouping by partner, id; the id line is a subgroup of partner),
        # we need to add the domain of the parent groupby criteria to the options
        sub_groupby_domain = []
        for markup, dummy, value in self.report_id._parse_line_id(line_dict_id):
            if markup.startswith('groupby:'):
                field_name = markup.split(':')[1]
                sub_groupby_domain.append((field_name, '=', value))

        if sub_groupby_domain:
            forced_domain = options.get('forced_domain', []) + sub_groupby_domain
            options = {**options, 'forced_domain': forced_domain}

        # When expanding subgroup lines, we need to keep track of the parent groupby lines, and build a domain from their grouping keys. This is
        # done by parsing the generic id of the current line.
        parent_groupby_domain = []
        for markup, dummy, value in reversed(self.env['account.report']._parse_line_id(line_dict_id)):
            if not markup.startswith('groupby:'):
                break

            field_name = markup.split(':')[1]
            parent_groupby_domain.append((field_name, '=', value))

        if parent_groupby_domain:
            options = {**options, 'forced_domain': options.get('forced_domain', []) + parent_groupby_domain}


        all_column_groups_expression_totals = self.report_id._compute_expression_totals_for_each_column_group(
            self.expression_ids,
            options,
            groupby_to_expand=groupby,
            offset=offset,
            limit=limit
        )

        # all_period_line_totals is a in the form [{report_line: {total_name: [(grouping_key, value)]}}]
        # Each element of the list corresponds to the values of a period (in sequence)

        # Put similar grouping keys from different totals/periods together, so that we don't display multiple
        # lines for the same grouping key

        figure_types_defaulting_to_0 = {'monetary', 'percentage', 'integer', 'float'}

        default_value_per_expr_label = {
            col_opt['expression_label']: 0 if col_opt['figure_type'] in figure_types_defaulting_to_0 else None
            for col_opt in options['columns']
        }
        aggregated_group_totals = {} # in the form {grouping key : [{expression: value} for each period]}
        for column_group_key, expression_totals in all_column_groups_expression_totals.items():
            for expression in self.expression_ids:
                for grouping_key, result in expression_totals[expression]['value']:
                    if expression.figure_type:
                        default_value = 0 if expression.figure_type in default_value_per_expr_label else None
                    else:
                        default_value = default_value_per_expr_label.get(expression.label)

                    aggregated_group_totals.setdefault(grouping_key, {key: defaultdict(lambda: {'value': default_value}) for key in all_column_groups_expression_totals})
                    aggregated_group_totals[grouping_key][column_group_key][expression] = {'value': result}

        # Generate groupby lines
        groupby_data = self._parse_groupby(groupby_to_expand=groupby)
        groupby_model = groupby_data['current_groupby_model']
        next_groupby = groupby_data['next_groupby']
        current_groupby = groupby_data['current_groupby']
        unfold_all = self.env.context.get('print_mode') and not options.get('unfolded_lines') or options.get('unfold_all')
        group_lines_by_keys = {}
        for grouping_key, group_totals in aggregated_group_totals.items():
            # For this, we emulate a dict formatted like the result of _compute_expression_totals_for_each_column_group, so that we can call
            # _build_static_line_columns like on non-grouped lines
            line_id = self.report_id._get_generic_line_id(groupby_model, grouping_key, parent_line_id=line_dict_id, markup=f'groupby:{current_groupby}')
            group_line_dict = {
                # 'name' key will be set later, so that we can browse all the records of this expansion at once (in case we're dealing with records)
                'id': line_id,
                'unfoldable': bool(next_groupby),
                'unfolded': unfold_all or line_id in options.get('unfolded_lines', {}),
                'groupby': next_groupby,
                'columns': self.report_id._build_static_line_columns(self, options, group_totals),
                'level': self.hierarchy_level + 2 * (len(sub_groupby_domain) + 1),
                'parent_id': line_dict_id,
                'expand_function': '_report_expand_unfoldable_line_with_groupby' if next_groupby else None,
                'caret_options': groupby_model if not next_groupby else None,
            }

            if self.report_id.custom_handler_model_id:
                self.env[self.report_id.custom_handler_model_name]._custom_groupby_line_completer(self.report_id, options, group_line_dict)

            # Growth comparison column.
            if self.report_id._display_growth_comparison(options):
                compared_expression = self.expression_ids.filtered(lambda expr: expr.label == group_line_dict['columns'][0]['expression_label'])
                group_line_dict['growth_comparison_data'] = self.report_id._compute_growth_comparison_column(
                    options, group_line_dict['columns'][0]['no_format'], group_line_dict['columns'][1]['no_format'], green_on_positive=compared_expression.green_on_positive)

            group_lines_by_keys[grouping_key] = group_line_dict

        # Sort grouping keys in the right order and generate line names
        keys_and_names_in_sequence = {}  # Order of this dict will matter

        if groupby_model:
            for record in self.env[groupby_model].browse(list(key for key in group_lines_by_keys if key is not None)).sorted():
                keys_and_names_in_sequence[record.id] = record.display_name

            if None in group_lines_by_keys:
                keys_and_names_in_sequence[None] = _("Unknown")

        else:
            for non_relational_key in sorted(group_lines_by_keys.keys()):
                keys_and_names_in_sequence[non_relational_key] = str(non_relational_key) if non_relational_key is not None else _("Unknown")

        # Build result: add a name to the groupby lines and handle totals below section for multi-level groupby
        group_lines = []
        for grouping_key, line_name in keys_and_names_in_sequence.items():
            group_line_dict = group_lines_by_keys[grouping_key]
            group_line_dict['name'] = line_name
            group_lines.append(group_line_dict)

            if next_groupby and self.env.company.totals_below_sections and any(col.get('no_format') is not None for col in group_line_dict['columns']):
                # This groupby has a sub-groupby, and is hence to be considered as some kind of section, meaning we need
                # a total line when using 'totals below section' option.
                group_line_dict['class'] = f"{group_line_dict.get('class', '')} o_account_reports_totals_below_sections"
                group_lines.append(self.report_id._generate_total_below_section_line(group_line_dict))

        return group_lines

    def _get_groupby_line_name(self, groupby_field_name, groupby_model, grouping_key):
        if groupby_model is None:
            return grouping_key

        if grouping_key is None:
            return _("Unknown")

        return self.env[groupby_model].browse(grouping_key).display_name

    def _parse_groupby(self, groupby_to_expand=None):
        """ Retrieves the information needed to handle the groupby feature on the current line.

        :param groupby_to_expand:    A coma-separated string containing, in order, all the fields that are used in the groupby we're expanding.
                                     None if we're not expanding anything.

        :return: A dictionary with 3 keys:
            'current_groupby':       The name of the field to be used on account.move.line to retrieve the results of the current groupby we're
                                     expanding, or None if nothing is being expanded

            'next_groupby':          The subsequent groupings to be applied after current_groupby, as a string of coma-separated field name.
                                     If no subsequent grouping exists, next_groupby will be None.

            'current_groupby_model': The model name corresponding to current_groupby, or None if current_groupby is None.

        EXAMPLE:
            When computing a line with groupby=partner_id,account_id,id , without expanding it:
            - groupby_to_expand will be None
            - current_groupby will be None
            - next_groupby will be 'partner_id,account_id,id'
            - current_groupby_model will be None

            When expanding the first group level of the line:
            - groupby_to_expand will be: partner_id,account_id,id
            - current_groupby will be 'partner_id'
            - next_groupby will be 'account_id,id'
            - current_groupby_model will be 'res.partner'

            When expanding further:
            - groupby_to_expand will be: account_id,id ; corresponding to the next_groupby computed when expanding partner_id
            - current_groupby will be 'account_id'
            - next_groupby will be 'id'
            - current_groupby_model will be 'account.account'
        """
        self.ensure_one()

        if groupby_to_expand:
            groupby_to_expand = groupby_to_expand.replace(' ', '')
            split_groupby = groupby_to_expand.split(',')
            current_groupby = split_groupby[0]
            next_groupby = ','.join(split_groupby[1:]) if len(split_groupby) > 1 else None
        else:
            current_groupby = None
            next_groupby = self.groupby.replace(' ', '') if self.groupby else None
            split_groupby = next_groupby.split(',') if next_groupby else []

        if current_groupby == 'id':
            groupby_model = 'account.move.line'
        elif current_groupby:
            groupby_model = self.env['account.move.line']._fields[current_groupby].comodel_name
        else:
            groupby_model = None

        return {
            'current_groupby': current_groupby,
            'next_groupby': next_groupby,
            'current_groupby_model': groupby_model,
        }


class AccountReportHorizontalGroup(models.Model):
    _name = "account.report.horizontal.group"
    _description = "Horizontal group for reports"

    name = fields.Char(string="Name", required=True, translate=True)
    rule_ids = fields.One2many(string="Rules", comodel_name='account.report.horizontal.group.rule', inverse_name='horizontal_group_id', required=True)
    report_ids = fields.Many2many(string="Reports", comodel_name='account.report')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "A horizontal group with the same name already exists."),
    ]

    def _get_header_levels_data(self):
        return [
            (rule.field_name, rule._get_matching_records())
            for rule in self.rule_ids
        ]

class AccountReportHorizontalGroupRule(models.Model):
    _name = "account.report.horizontal.group.rule"
    _description = "Horizontal group rule for reports"

    def _field_name_selection_values(self):
        return [
            (aml_field['name'], aml_field['string'])
            for aml_field in self.env['account.move.line'].fields_get().values()
            if aml_field['type'] in ('many2one', 'many2many')
        ]

    horizontal_group_id = fields.Many2one(string="Horizontal Group", comodel_name='account.report.horizontal.group', required=True)
    domain = fields.Char(string="Domain", required=True, default='[]')
    field_name = fields.Selection(string="Field", selection='_field_name_selection_values', required=True)
    res_model_name = fields.Char(string="Model", compute='_compute_res_model_name')

    @api.depends('field_name')
    def _compute_res_model_name(self):
        for record in self:
            if record.field_name:
                record.res_model_name = self.env['account.move.line']._fields[record.field_name].comodel_name
            else:
                record.res_model_name = None

    def _get_matching_records(self):
        self.ensure_one()
        model_name = self.env['account.move.line']._fields[self.field_name].comodel_name
        domain = ast.literal_eval(self.domain)
        return self.env[model_name].search(domain)


class AccountReportCustomHandler(models.AbstractModel):
    _name = 'account.report.custom.handler'
    _description = 'Account Report Custom Handler'

    # This abstract model allows case-by-case localized changes of behaviors of reports.
    # This is used for custom reports, for cases that cannot be supported by the standard engines.

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        """ Generates lines dynamically for reports that require a custom processing which cannot be handled
        by regular report engines.
        :return:    A list of tuples [(sequence, line_dict), ...], where:
                    - sequence is the sequence to apply when rendering the line (can be mixed with static lines),
                    - line_dict is a dict containing all the line values.
        """
        return []

    def _caret_options_initializer(self):
        """ Returns the caret options dict to be used when rendering this report,
        in the same format as the one used in _caret_options_initializer_default (defined on 'account.report').
        If the result is empty, the engine will use the default caret options.
        """
        return self.env['account.report']._caret_options_initializer_default()

    def _custom_options_initializer(self, report, options, previous_options=None):
        """ To be overridden to add report-specific _init_options... code to the report. """
        if report.root_report_id and not hasattr(report, '_init_options_custom'):
            report.root_report_id._init_options_custom(options, previous_options)

    def _custom_line_postprocessor(self, report, options, lines):
        """ Postprocesses the result of the report's _get_lines() before returning it. """
        return lines

    def _custom_groupby_line_completer(self, report, options, line_dict):
        """ Postprocesses the dict generated by the group_by_line, to customize its content. """

    def _custom_unfold_all_batch_data_generator(self, report, options, lines_to_expand_by_function):
        """ When using the 'unfold all' option, some reports might end up recomputing the same query for
        each line to unfold, leading to very inefficient computation. This function allows batching this computation,
        and returns a dictionary where all results are cached, for use in expansion functions.
        """
        return None
