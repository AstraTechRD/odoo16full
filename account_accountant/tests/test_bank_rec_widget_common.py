# -*- coding: utf-8 -*-
from lxml import etree

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form


class WizardForm(Form):
    """ Hack the current ORM form to emulate the bank reconciliation widget.
    Indeed, the current implementation doesn't work with the new record.
    """

    def __init__(self, recordp, view=None):
        # EXTENDS base
        # Prevent the trigger of the "editing unstored records is not supported" error.
        object.__setattr__(self, 'bankRecWidget', recordp)
        super().__init__(recordp.browse(), view=view)

    def _init_from_defaults(self, model):
        # EXTENDS base
        # Initialize the wizard with the default provided record.
        widget = self.bankRecWidget
        if widget:
            fields_info = self._view['fields']
            values = {
                fieldname: widget._fields[fieldname].convert_to_write(widget[fieldname], widget)
                for fieldname in fields_info.keys()
            }
            self._values.update(values)
        else:
            super()._init_from_defaults(model)

    def save(self):
        # EXTENDS base
        return self.bankRecWidget.new(self._values)


class TestBankRecWidgetCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.currency_data_2 = cls.setup_multi_currency_data(default_values={
            'name': 'Dark Chocolate Coin',
            'symbol': '🍫',
            'currency_unit_label': 'Dark Choco',
            'currency_subunit_label': 'Dark Cacao Powder',
        }, rate2016=6.0, rate2017=4.0)
        cls.currency_data_3 = cls.setup_multi_currency_data(default_values={
            'name': 'Black Chocolate Coin',
            'symbol': '🍫',
            'currency_unit_label': 'Black Choco',
            'currency_subunit_label': 'Black Cacao Powder',
        }, rate2016=12.0, rate2017=8.0)

        # <field name="todo_command" invisible="1"/>
        # This test tests the onchange behvior of todo_command, `_onchange_todo_command`
        # But `todo_command` is always invisible in the view, and shouldn't be able to changed in the form by a user
        # The fact it gets changed is thanks to a custom js widget changing the value of the field even if invisible.
        view = cls.env.ref('account_accountant.view_bank_rec_widget_form')
        tree = etree.fromstring(view.arch)
        for node in tree.xpath('//field[@name="todo_command"]'):
            del node.attrib['invisible']
        view.arch = etree.tostring(tree)

    @classmethod
    def _create_invoice_line(cls, move_type, **kwargs):
        ''' Create an invoice on the fly.'''

        def setvalue(proxy, field, value):
            descr = proxy._view['fields'].get(field)
            if descr['type'] == 'one2many':
                for one2many_values in value:
                    with proxy.__getattr__(field).new() as one2many_proxy:
                        for one2many_field, one2many_field_value in one2many_values.items():
                            setvalue(one2many_proxy, one2many_field, one2many_field_value)
            elif descr['type'] == 'many2many':
                many2many_proxy = proxy.__getattr__(field)
                many2many_proxy.clear()
                for many2many_value in value:
                    many2many_proxy.add(many2many_value)
            else:
                proxy.__setattr__(field, value)

        kwargs.setdefault('partner_id', cls.partner_a)
        kwargs.setdefault('invoice_date', '2017-01-01')
        kwargs.setdefault('invoice_line_ids', [])
        for one2many_values in kwargs['invoice_line_ids']:
            one2many_values.setdefault('name', 'xxxx')
            one2many_values.setdefault('quantity', 1)
            one2many_values.setdefault('tax_ids', cls.env['account.tax'])

        invoice_form = Form(cls.env['account.move'].with_context(default_move_type=move_type))
        for field, field_value in kwargs.items():
            setvalue(invoice_form, field, field_value)
        invoice = invoice_form.save()
        invoice.action_post()
        lines = invoice.line_ids
        return lines.filtered(lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable'))

    @classmethod
    def _create_st_line(cls, amount, date='2019-01-01', payment_ref='turlututu', **kwargs):
        return cls.env['account.bank.statement.line'].create({
            'amount': amount,
            'date': date,
            'payment_ref': payment_ref,
            'journal_id': kwargs.get('journal_id', cls.company_data['default_journal_bank'].id),
            **kwargs,
        })

    @classmethod
    def _create_reconcile_model(cls, **kwargs):
        return cls.env['account.reconcile.model'].create({
            'name': "test",
            'rule_type': 'invoice_matching',
            'allow_payment_tolerance': True,
            'payment_tolerance_type': 'percentage',
            'payment_tolerance_param': 0.0,
            **kwargs,
            'line_ids': [
                Command.create({
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'amount_type': 'percentage',
                    'label': f"test {i}",
                    **line_vals,
                })
                for i, line_vals in enumerate(kwargs.get('line_ids', []))
            ],
        })
