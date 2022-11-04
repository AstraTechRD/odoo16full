# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo.http import request
from odoo import _lt

from datetime import datetime


def currency_normalisation(sql_result, sum_name):
    result = 0
    currencies = request.env['res.currency'].browse(
        [row['currency_id'] for row in sql_result if row.get('currency_id')]
        + [row['company_currency_id'] for row in sql_result if row.get('company_currency_id')])
    currencies_mapped = {c.id: c for c in currencies}
    for row in sql_result:
        if not row.get('currency_id'):
            # account move line in the same currency than the company currency
            amount = row[sum_name]
        else:
            currency_id = currencies_mapped[row['currency_id']]
            company_currency_id = currencies_mapped[row['company_currency_id']]
            amount_foreign_cur = row[sum_name]
            company_id = request.env.company
            amount = currency_id._convert(
                from_amount=amount_foreign_cur, to_currency=company_currency_id,
                company=company_id, date=datetime.utcnow().date())
        result += amount
    return result

def _execute_sql_query(fields, tables, conditions, query_args, filters, groupby=None):
    """ Returns the result of the SQL query. """
    query, args = _build_sql_query(fields, tables, conditions, query_args, filters, groupby=groupby)
    request.cr.execute(query, args)
    return request.cr.dictfetchall()


def _build_sql_query(fields, tables, conditions, query_args, filters, groupby=None):
    """ The goal of this function is to avoid:
        * writing raw SQL requests (kind of abstraction)
        * writing additionnal conditions for filters (same conditions for every request)
    :params fields, tables, conditions: basic SQL request statements
    :params query_args: dict of optional query args used in the request
    :params filters: dict of optional filters (template_ids, tag_ids, company_ids)
    :params groupby: additionnal groupby statement

    :returns: the SQL request and the new query_args (with filters tables & conditions)
    """
    # The conditions should use named arguments and these arguments are in query_args.

    if filters.get('template_ids'):
        tables.append("sale_order")
        conditions.append("account_move_line.subscription_id = sale_order.id")
        conditions.append("sale_order.sale_order_template_id IN %(template_ids)s")
        query_args['template_ids'] = tuple(filters.get('template_ids'))

    if filters.get('sale_team_ids'):
        tables.append("crm_team")
        conditions.append("account_move.team_id = crm_team.id")
        conditions.append("crm_team.id IN %(team_ids)s")
        query_args['team_ids'] = tuple(filters.get('sale_team_ids'))

    if filters.get('company_ids'):
        conditions.append("account_move.company_id IN %(company_ids)s")
        conditions.append("account_move_line.company_id IN %(company_ids)s")
        query_args['company_ids'] = tuple(filters.get('company_ids'))

    fields_str = ', '.join(set(fields))
    tables_str = ', '.join(set(tables))
    conditions_str = ' AND '.join(set(conditions))

    if groupby:
        base_query = "SELECT %s FROM %s WHERE %s GROUP BY %s" % (fields_str, tables_str, conditions_str, groupby)
    else:
        base_query = "SELECT %s FROM %s WHERE %s" % (fields_str, tables_str, conditions_str)

    return base_query, query_args


def compute_net_revenue(start_date, end_date, filters):
    fields = ['account_move_line.price_subtotal,account_move_line.currency_id,account_move_line.company_currency_id']
    tables = ['account_move_line', 'account_move']
    conditions = [
        "account_move.invoice_date BETWEEN %(start_date)s AND %(end_date)s",
        "account_move_line.move_id = account_move.id",
        "account_move.move_type IN ('out_invoice', 'out_refund')",
        "account_move.state NOT IN ('draft', 'cancel')",
        "account_move_line.display_type = 'product'",
    ]

    sql_results = _execute_sql_query(fields, tables, conditions, {
        'start_date': start_date,
        'end_date': end_date,
    }, filters)

    return currency_normalisation(sql_results, 'price_subtotal')


def compute_arpu(start_date, end_date, filters):
    mrr = compute_mrr(start_date, end_date, filters)
    nb_customers = compute_nb_contracts(start_date, end_date, filters)
    result = 0 if not nb_customers else mrr/float(nb_customers)
    return int(result)


def compute_arr(start_date, end_date, filters):
    result = 12*compute_mrr(start_date, end_date, filters)
    return int(result)


def compute_ltv(start_date, end_date, filters):
    fields = ['account_move_line.subscription_mrr', 'account_move_line.subscription_id',
              'account_move_line.currency_id', 'account_move_line.company_currency_id', 'account_move_line.company_id']
    tables = ['account_move_line', 'account_move']
    conditions = [
        "date %(date)s BETWEEN account_move_line.subscription_start_date AND account_move_line.subscription_end_date",
        "account_move.id = account_move_line.move_id",
        "account_move.move_type IN ('out_invoice', 'out_refund')",
        "account_move.state NOT IN ('draft', 'cancel')"
    ]

    sql_results = _execute_sql_query(fields, tables, conditions, {
        'date': end_date,
    }, filters)

    sum_mrr = currency_normalisation(sql_results, 'subscription_mrr')
    n_customer = len({x['subscription_id'] for x in sql_results})
    avg_mrr_per_customer = sum_mrr/n_customer if n_customer else 0
    logo_churn = compute_logo_churn(start_date, end_date, filters)
    result = 0 if logo_churn == 0 else avg_mrr_per_customer/float(logo_churn)
    return int(result)


def compute_nrr(start_date, end_date, filters):
    fields = ['account_move_line.price_subtotal', 'account_move_line.currency_id',
              'account_move_line.company_currency_id', 'account_move_line.company_id']
    tables = ['account_move_line', 'account_move']
    conditions = [
        "(account_move.invoice_date BETWEEN %(start_date)s AND %(end_date)s)",
        "account_move_line.move_id = account_move.id",
        "account_move.move_type IN ('out_invoice', 'out_refund')",
        "account_move.state NOT IN ('draft', 'cancel')",
        "account_move_line.subscription_start_date IS NULL",
        "account_move_line.display_type = 'product'",
    ]

    sql_results = _execute_sql_query(fields, tables, conditions, {
        'start_date': start_date,
        'end_date': end_date,
    }, filters)
    return currency_normalisation(sql_results, 'price_subtotal')


def compute_nb_contracts(start_date, end_date, filters):
    fields = ['COUNT(DISTINCT account_move_line.subscription_id) AS sum']
    tables = ['account_move_line', 'account_move']
    conditions = [
        "date %(date)s BETWEEN account_move_line.subscription_start_date AND account_move_line.subscription_end_date",
        "account_move.id = account_move_line.move_id",
        "account_move.move_type IN ('out_invoice', 'out_refund')",
        "account_move.state NOT IN ('draft', 'cancel')",
        "account_move_line.subscription_id IS NOT NULL"
    ]

    sql_results = _execute_sql_query(fields, tables, conditions, {
        'date': end_date,
    }, filters)

    return 0 if not sql_results or not sql_results[0]['sum'] else sql_results[0]['sum']


def compute_mrr(start_date, end_date, filters):
    fields = ["account_move_line.subscription_mrr as subscription_mrr",
              'account_move_line.currency_id', 'account_move_line.company_currency_id', 'account_move_line.company_id']
    tables = ['account_move_line', 'account_move']
    conditions = [
        "date %(date)s BETWEEN account_move_line.subscription_start_date AND account_move_line.subscription_end_date",
        "account_move.id = account_move_line.move_id",
        "account_move.move_type IN ('out_invoice', 'out_refund')",
        "account_move.state NOT IN ('draft', 'cancel')"
    ]

    sql_results = _execute_sql_query(fields, tables, conditions, {
        'date': end_date,
    }, filters)

    return currency_normalisation(sql_results, 'subscription_mrr')


def compute_logo_churn(start_date, end_date, filters):

    fields = ['COUNT(DISTINCT account_move_line.subscription_id) AS sum']
    tables = ['account_move_line', 'account_move']
    conditions = [
        "date %(date)s - interval '1 months' BETWEEN account_move_line.subscription_start_date AND account_move_line.subscription_end_date",
        "account_move.id = account_move_line.move_id",
        "account_move.move_type IN ('out_invoice', 'out_refund')",
        "account_move.state NOT IN ('draft', 'cancel')",
        "account_move_line.subscription_id IS NOT NULL"
    ]

    sql_results = _execute_sql_query(fields, tables, conditions, {
        'date': end_date,
    }, filters)

    active_customers_1_month_ago = 0 if not sql_results or not sql_results[0]['sum'] else sql_results[0]['sum']

    fields = ['COUNT(DISTINCT account_move_line.subscription_id) AS sum']
    tables = ['account_move_line', 'account_move']
    conditions = [
        "date %(date)s - interval '1 months' BETWEEN account_move_line.subscription_start_date AND account_move_line.subscription_end_date",
        "account_move.id = account_move_line.move_id",
        "account_move.move_type IN ('out_invoice', 'out_refund')",
        "account_move.state NOT IN ('draft', 'cancel')",
        "account_move_line.subscription_id IS NOT NULL",
        """NOT exists (
                    SELECT 1 from account_move_line ail
                    WHERE ail.subscription_id = account_move_line.subscription_id
                    AND (date %(date)s BETWEEN ail.subscription_start_date AND ail.subscription_end_date)
                )
        """,
    ]

    sql_results = _execute_sql_query(fields, tables, conditions, {
        'date': end_date,
    }, filters)

    resigned_customers = 0 if not sql_results or not sql_results[0]['sum'] else sql_results[0]['sum']

    return 0 if not active_customers_1_month_ago else 100*resigned_customers/float(active_customers_1_month_ago)


def compute_revenue_churn(start_date, end_date, filters):

    fields = ['account_move_line.subscription_mrr,account_move_line.currency_id,account_move_line.company_currency_id',
              'account_move_line.company_id']
    tables = ['account_move_line', 'account_move']
    conditions = [
        "date %(date)s - interval '1 months' BETWEEN account_move_line.subscription_start_date AND account_move_line.subscription_end_date",
        "account_move.id = account_move_line.move_id",
        "account_move.move_type IN ('out_invoice', 'out_refund')",
        "account_move.state NOT IN ('draft', 'cancel')",
        "account_move_line.subscription_id IS NOT NULL",
        """NOT exists (
                    SELECT 1 from account_move_line ail
                    WHERE ail.subscription_id = account_move_line.subscription_id
                    AND (date %(date)s BETWEEN ail.subscription_start_date AND ail.subscription_end_date)
                )
        """
    ]

    sql_results = _execute_sql_query(fields, tables, conditions, {
        'date': end_date,
    }, filters)

    churned_mrr = currency_normalisation(sql_results, 'subscription_mrr')
    previous_month_mrr = compute_mrr(start_date, (end_date - relativedelta(months=+1)), filters)
    return 0 if previous_month_mrr == 0 else 100*churned_mrr/float(previous_month_mrr)


def compute_mrr_growth_values(start_date, end_date, filters):
    new_mrr = 0
    expansion_mrr = 0
    down_mrr = 0
    churned_mrr = 0
    net_new_mrr = 0

    # 1. NEW
    fields = ['account_move_line.subscription_mrr,account_move_line.currency_id,account_move_line.company_currency_id',
              'account_move_line.company_id']
    tables = ['account_move_line', 'account_move']
    conditions = [
        "date %(date)s BETWEEN account_move_line.subscription_start_date AND account_move_line.subscription_end_date",
        "account_move.id = account_move_line.move_id",
        "account_move.move_type IN ('out_invoice', 'out_refund')",
        "account_move.state NOT IN ('draft', 'cancel')",
        "account_move_line.subscription_id IS NOT NULL",
        """NOT exists (
                    SELECT 1 from account_move_line ail
                    WHERE ail.subscription_id = account_move_line.subscription_id
                    AND (date %(date)s - interval '1 months' BETWEEN ail.subscription_start_date AND ail.subscription_end_date)
                )
        """
    ]

    sql_results = _execute_sql_query(fields, tables, conditions, {
        'date': end_date,
    }, filters)

    new_mrr = currency_normalisation(sql_results, 'subscription_mrr')

    # 2. DOWN & EXPANSION
    ##############################
    # We rely on the sale_order_log value because comparing aml evolution is too verbose
    # with currency conversion.
    # The log already have the converted currencies.

    fields = ['sale_order_log.amount_company_currency AS diff']
    tables = ['sale_order_log', 'sale_order_template', 'sale_order']
    conditions = [
        "sale_order_log.event_type = '1_change'",
        "sale_order_template.id = sale_order.sale_order_template_id",
        "sale_order.id = sale_order_log.order_id",
        "sale_order_log.event_date >= %(date)s",
        "sale_order_log.event_date >= %(date)s",
    ]

    query_args = {'date': end_date}
    if filters.get('template_ids'):
        conditions.append("sale_order_template.id IN %(template_ids)s")
        query_args['template_ids'] = tuple(filters.get('template_ids'))

    if filters.get('sale_team_ids'):
        conditions.append("sale_order_log.team_id IN %(team_ids)s")
        conditions.append("sale_order.team_id IN %(team_ids)s")
        query_args['team_ids'] = tuple(filters.get('sale_team_ids'))

    if filters.get('company_ids'):
        conditions.append("sale_order_log.company_id IN %(company_ids)s")
        conditions.append("sale_order.company_id IN %(company_ids)s")
        query_args['company_ids'] = tuple(filters.get('company_ids'))

    # Filters are empty in the following call because we took care above
    sql_results = _execute_sql_query(fields, tables, conditions, query_args, {})

    for account in sql_results:
        if account['diff'] > 0:
            expansion_mrr += account['diff']
        else:
            down_mrr -= account['diff']

    # 3. CHURNED
    fields = ['account_move_line.subscription_mrr']
    tables = ['account_move_line', 'account_move']
    conditions = [
        "date %(date)s - interval '1 months' BETWEEN account_move_line.subscription_start_date AND account_move_line.subscription_end_date",
        "account_move.id = account_move_line.move_id",
        "account_move.move_type IN ('out_invoice', 'out_refund')",
        "account_move.state NOT IN ('draft', 'cancel')",
        "account_move_line.subscription_id IS NOT NULL",
        """NOT exists (
                    SELECT 1 from account_move_line ail
                    WHERE ail.subscription_id = account_move_line.subscription_id
                    AND (date %(date)s BETWEEN ail.subscription_start_date AND ail.subscription_end_date)
                )
        """,
    ]

    sql_results = _execute_sql_query(fields, tables, conditions, {
        'date': end_date,
    }, filters)

    churned_mrr = currency_normalisation(sql_results, 'subscription_mrr')

    net_new_mrr = new_mrr - churned_mrr + expansion_mrr - down_mrr

    return {
        'new_mrr': new_mrr,
        'churned_mrr': -churned_mrr,
        'expansion_mrr': expansion_mrr,
        'down_mrr': -down_mrr,
        'net_new_mrr': net_new_mrr,
    }


STAT_TYPES = {
    'mrr': {
        'name': _lt('Monthly Recurring Revenue'),
        'code': 'mrr',
        'tooltip': _lt('MRR for short; total subscription revenue per month (e.g. for an annual subscription of $ 1,200, the MRR is $ 100)'),
        'dir': 'up',
        'prior': 1,
        'type': 'last',
        'add_symbol': 'currency',
        'compute': compute_mrr
    },
    'net_revenue': {
        'name': _lt('Net Revenue'),
        'code': 'net_revenue',
        'tooltip': _lt('Total net revenue (all invoices emitted during the period)'),
        'dir': 'up',
        'prior': 2,
        'type': 'sum',
        'add_symbol': 'currency',
        'compute': compute_net_revenue
    },
    'nrr': {
        'name': _lt('Non-Recurring Revenue'),
        'code': 'nrr',
        'tooltip': _lt('One-shot revenue that is not part of a subscription'),
        'dir': 'up',  # 'down' if fees ?
        'prior': 3,
        'type': 'sum',
        'add_symbol': 'currency',
        'compute': compute_nrr
    },
    'arpu': {
        'name': _lt('Revenue per Subscription'),
        'code': 'arpu',
        'tooltip': _lt('Average revenue of a subscription, obtained by dividing the MRR by the number of subscriptions'),
        'dir': 'up',
        'prior': 4,
        'type': 'last',
        'add_symbol': 'currency',
        'compute': compute_arpu
    },
    'arr': {
        'name': _lt('Annual Run-Rate'),
        'code': 'arr',
        'tooltip': _lt('Yearly version of the MRR, obtained by multiplying the MRR by 12'),
        'dir': 'up',
        'prior': 5,
        'type': 'last',
        'add_symbol': 'currency',
        'compute': compute_arr
    },
    'ltv': {
        'name': _lt('Lifetime Value'),
        'code': 'ltv',
        'tooltip': _lt('Expected lifetime revenue of an average subscription; obtained by dividing the average MRR of a subscription by the churn rate (e.g. if your average MRR is $ 100 and your churn rate is 5%, the LTV will be $ 100/5% = $ 2,000)'),
        'dir': 'up',
        'prior': 6,
        'type': 'last',
        'add_symbol': 'currency',
        'compute': compute_ltv
    },
    'logo_churn': {
        'name': _lt('Customer Churn'),
        'code': 'logo_churn',
        'tooltip': _lt('Number of subscriptions that gets closed during a period'),
        'dir': 'down',
        'prior': 7,
        'type': 'last',
        'add_symbol': '%',
        'compute': compute_logo_churn
    },
    'revenue_churn': {
        'name': _lt('Revenue Churn'),
        'code': 'revenue_churn',
        'tooltip': _lt('Reduction in total MRR over the period'),
        'dir': 'down',
        'prior': 8,
        'type': 'last',
        'add_symbol': '%',
        'compute': compute_revenue_churn
    },
    'nb_contracts': {
        'name': _lt('# Subscriptions'),
        'code': 'nb_contracts',
        'tooltip': _lt('Number of contracts'),
        'dir': 'up',
        'prior': 9,
        'type': 'last',
        'add_symbol': '',
        'compute': compute_nb_contracts
    },
}

FORECAST_STAT_TYPES = {
    'mrr_forecast': {
        'name': _lt('Forecasted Annual MRR Growth'),
        'code': 'mrr_forecast',
        'tooltip': _lt('Total subscription revenue per month (e.g. for an annual subscription of $ 1,200, the MRR is $ 100)'),
        'prior': 1,
        'add_symbol': 'currency',
    },
    'contracts_forecast': {
        'name': _lt('Forecasted Annual Subscriptions Growth'),
        'code': 'contracts_forecast',
        'tooltip': _lt('Total subscription revenue per month (e.g. for an annual subscription of $ 1,200, the MRR is $ 100)'),
        'prior': 2,
        'add_symbol': '',
    },
}
