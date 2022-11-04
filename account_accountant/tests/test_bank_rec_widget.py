# -*- coding: utf-8 -*-
from odoo.addons.account_accountant.tests.test_bank_rec_widget_common import TestBankRecWidgetCommon, WizardForm
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import html2plaintext
from odoo import fields, Command

from freezegun import freeze_time
import re


@tagged('post_install', '-at_install')
class TestBankRecWidget(TestBankRecWidgetCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.early_payment_term = cls.env['account.payment.term'].create({
            'name': "early_payment_term",
            'company_id': cls.company_data['company'].id,
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 10,
                    'days': 5,
                }),
                Command.create({
                    'value': 'percent',
                    'value_amount': 20,
                    'days': 20,
                    'discount_percentage': 5,
                    'discount_days': 10,
                }),
                Command.create({
                    'value': 'percent',
                    'value_amount': 40,
                    'days': 40,
                    'discount_percentage': 10,
                    'discount_days': 35,
                }),
                Command.create({
                    'value': 'balance',
                    'days': 50,
                }),
            ],
        })

        cls.account_revenue1 = cls.company_data['default_account_revenue']
        cls.account_revenue2 = cls.copy_account(cls.account_revenue1)

    def assert_form_extra_text_value(self, value, regex):
        if regex:
            cleaned_value = html2plaintext(value).replace('\n', '')
            if not re.match(regex, cleaned_value):
                self.fail(f"The following 'form_extra_text':\n\n'{cleaned_value}'\n\n...doesn't match the provided regex:\n\n'{regex}'")
        else:
            self.assertFalse(value)

    def test_retrieve_partner_from_account_number(self):
        st_line = self._create_st_line(1000.0, partner_id=None, account_number="014 474 8555")
        bank_account = self.env['res.partner.bank'].create({
            'acc_number': '0144748555',
            'partner_id': self.partner_a.id,
        })
        self.assertEqual(st_line._retrieve_partner(), bank_account.partner_id)

        # Can't retrieve the partner since the bank account is used by multiple partners.
        self.env['res.partner.bank'].create({
            'acc_number': '0144748555',
            'partner_id': self.partner_b.id,
        })
        self.assertEqual(st_line._retrieve_partner(), self.env['res.partner'])

    def test_retrieve_partner_from_payment_ref(self):
        st_line = self._create_st_line(1000.0, partner_id=None, payment_ref="Gagnant turlututu Bernard tsoin tsoin")
        partner = self.env['res.partner'].create({'name': "Bernard Gagnant"})
        self._create_invoice_line(
            'out_invoice',
            partner_id=partner,
            invoice_date='2019-01-01',
            invoice_line_ids=[{'price_unit': 1000.0}],
        )

        self.assertEqual(st_line._retrieve_partner(), partner)

    def test_validation_new_aml_same_foreign_currency(self):
        # 6000.0 curr2 == 1200.0 comp_curr (bank rate 5:1 instead of the odoo rate 4:1)
        st_line = self._create_st_line(
            1200.0,
            date='2017-01-01',
            foreign_currency_id=self.currency_data_2['currency'].id,
            amount_currency=6000.0,
        )
        # 6000.0 curr2 == 1000.0 comp_curr (rate 6:1)
        inv_line = self._create_invoice_line(
            'out_invoice',
            currency_id=self.currency_data_2['currency'],
            invoice_date='2016-01-01',
            invoice_line_ids=[{'price_unit': 6000.0}],
        )

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_amls(inv_line)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',   'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0},
            {'flag': 'new_aml',     'amount_currency': -6000.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1200.0},
        ])
        self.assertRecordValues(wizard, [{'state': 'valid'}])

        # The amount is the same, no message under the 'amount' field.
        self.assert_form_extra_text_value(wizard.form_extra_text, False)

        wizard.button_validate(async_action=False)
        self.assertRecordValues(st_line.line_ids, [
            # pylint: disable=C0326
            {'account_id': st_line.journal_id.default_account_id.id,    'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0,  'reconciled': False},
            {'account_id': inv_line.account_id.id,                      'amount_currency': -6000.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1200.0, 'reconciled': True},
        ])
        self.assertRecordValues(st_line, [{'is_reconciled': True}])
        self.assertRecordValues(inv_line.move_id, [{'payment_state': 'paid'}])

        # Reset the wizard.
        wizard.button_reset()
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0},
            {'flag': 'auto_balance',    'amount_currency': -6000.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1200.0},
        ])

        # Create the same invoice with a higher amount to check the partial flow.
        # 9000.0 curr2 == 1500.0 comp_curr (rate 6:1)
        inv_line = self._create_invoice_line(
            'out_invoice',
            currency_id=self.currency_data_2['currency'],
            invoice_date='2016-01-01',
            invoice_line_ids=[{'price_unit': 9000.0}],
        )
        wizard._action_add_new_amls(inv_line)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',   'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0},
            {'flag': 'new_aml',     'amount_currency': -6000.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1200.0},
        ])

        # Check the message under the 'amount' field.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'new_aml')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        wizard = form.save()
        self.assert_form_extra_text_value(
            wizard.form_extra_text,
            r".+open amount of 9,000.000.+ reduced by 6,000.000.+ set the invoice as fully paid .",
        )
        self.assertRecordValues(wizard, [{
            'form_suggest_amount_currency': 9000.0,
            'form_suggest_balance': 1800.0,
        }])

        # Switch to a full reconciliation.
        form = WizardForm(wizard)
        form.todo_command = 'button_clicked,button_form_apply_suggestion'
        wizard = form.save()
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0},
            {'flag': 'new_aml',         'amount_currency': -9000.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1800.0},
            {'flag': 'auto_balance',    'amount_currency': 3000.0,      'currency_id': self.currency_data_2['currency'].id, 'balance': 600.0},
        ])

        # Check the message under the 'amount' field.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'new_aml')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        wizard = form.save()
        self.assert_form_extra_text_value(
            wizard.form_extra_text,
            r".+open amount of 9,000.000.+ paid .+ record a partial payment .",
        )
        self.assertRecordValues(wizard, [{
            'form_suggest_amount_currency': 6000.0,
            'form_suggest_balance': 1200.0,
        }])

        # Switch back to a partial reconciliation.
        form = WizardForm(wizard)
        form.todo_command = 'button_clicked,button_form_apply_suggestion'
        wizard = form.save()
        self.assertRecordValues(wizard, [{'state': 'valid'}])

        # Reconcile
        wizard.button_validate(async_action=False)
        self.assertRecordValues(st_line.line_ids, [
            # pylint: disable=C0326
            {'account_id': st_line.journal_id.default_account_id.id,    'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0,  'reconciled': False},
            {'account_id': inv_line.account_id.id,                      'amount_currency': -6000.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1200.0, 'reconciled': True},
        ])
        self.assertRecordValues(st_line, [{'is_reconciled': True}])
        self.assertRecordValues(inv_line.move_id, [{
            'payment_state': 'partial',
            'amount_residual': 3000.0,
        }])

    def test_validation_new_aml_one_foreign_currency_on_st_line(self):
        # 4800.0 curr2 == 1200.0 comp_curr (rate 4:1)
        st_line = self._create_st_line(
            1200.0,
            date='2017-01-01',
            foreign_currency_id=self.currency_data_2['currency'].id,
            amount_currency=4800.0,
        )
        # 800.0 comp_curr is equals to 4800.0 curr2 in 2016 (rate 6:1)
        inv_line = self._create_invoice_line(
            'out_invoice',
            invoice_date='2016-01-01',
            invoice_line_ids=[{'price_unit': 800.0}],
        )

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_amls(inv_line)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',   'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0},
            {'flag': 'new_aml',     'amount_currency': -4800.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1200.0},
        ])
        self.assertRecordValues(wizard, [{'state': 'valid'}])

        # The amount is the same, no message under the 'amount' field.
        self.assert_form_extra_text_value(wizard.form_extra_text, False)

        wizard.button_validate(async_action=False)
        self.assertRecordValues(st_line.line_ids, [
            # pylint: disable=C0326
            {'account_id': st_line.journal_id.default_account_id.id,    'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0,  'reconciled': False},
            {'account_id': inv_line.account_id.id,                      'amount_currency': -4800.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1200.0, 'reconciled': True},
        ])
        self.assertRecordValues(st_line, [{'is_reconciled': True}])
        self.assertRecordValues(inv_line.move_id, [{'payment_state': 'paid'}])

        # Reset the wizard.
        wizard.button_reset()
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0},
            {'flag': 'auto_balance',    'amount_currency': -4800.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1200.0},
        ])

        # Create the same invoice with a higher amount to check the partial flow.
        # 1200.0 comp_curr is equals to 7200.0 curr2 in 2016 (rate 6:1)
        inv_line = self._create_invoice_line(
            'out_invoice',
            invoice_date='2016-01-01',
            invoice_line_ids=[{'price_unit': 1200.0}],
        )
        wizard._action_add_new_amls(inv_line)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',   'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0},
            {'flag': 'new_aml',     'amount_currency': -4800.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1200.0},
        ])

        # Check the message under the 'amount' field.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'new_aml')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        wizard = form.save()
        self.assert_form_extra_text_value(
            wizard.form_extra_text,
            r".+open amount of .+1,200.00.+ reduced by .+800.00.+ set the invoice as fully paid .",
        )
        self.assertRecordValues(wizard, [{
            'form_suggest_amount_currency': 7200.0,
            'form_suggest_balance': 1800.0,
        }])

        # Switch to a full reconciliation.
        form = WizardForm(wizard)
        form.todo_command = 'button_clicked,button_form_apply_suggestion'
        wizard = form.save()
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0},
            {'flag': 'new_aml',         'amount_currency': -7200.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1800.0},
            {'flag': 'auto_balance',    'amount_currency': 2400.0,      'currency_id': self.currency_data_2['currency'].id, 'balance': 600.0},
        ])

        # Check the message under the 'amount' field.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'new_aml')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        wizard = form.save()
        self.assert_form_extra_text_value(
            wizard.form_extra_text,
            r".+open amount of .+1,200.00.+ paid .+ record a partial payment .",
        )
        self.assertRecordValues(wizard, [{
            'form_suggest_amount_currency': 4800.0,
            'form_suggest_balance': 1200.0,
        }])

        # Switch back to a partial reconciliation.
        form = WizardForm(wizard)
        form.todo_command = 'button_clicked,button_form_apply_suggestion'
        wizard = form.save()
        self.assertRecordValues(wizard, [{'state': 'valid'}])

        # Reconcile
        wizard.button_validate(async_action=False)
        self.assertRecordValues(st_line.line_ids, [
            # pylint: disable=C0326
            {'account_id': st_line.journal_id.default_account_id.id,    'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0,  'reconciled': False},
            {'account_id': inv_line.account_id.id,                      'amount_currency': -4800.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1200.0, 'reconciled': True},
        ])
        self.assertRecordValues(st_line, [{'is_reconciled': True}])
        self.assertRecordValues(inv_line.move_id, [{
            'payment_state': 'partial',
            'amount_residual': 400.0,
        }])

    def test_validation_new_aml_one_foreign_currency_on_inv_line(self):
        # 1200.0 comp_curr is equals to 4800.0 curr2 in 2017 (rate 4:1)
        st_line = self._create_st_line(
            1200.0,
            date='2017-01-01',
        )
        # 4800.0 curr2 == 800.0 comp_curr (rate 6:1)
        inv_line = self._create_invoice_line(
            'out_invoice',
            currency_id=self.currency_data_2['currency'],
            invoice_date='2016-01-01',
            invoice_line_ids=[{'price_unit': 4800.0}],
        )

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_amls(inv_line)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',   'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0},
            {'flag': 'new_aml',     'amount_currency': -4800.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1200.0},
        ])
        self.assertRecordValues(wizard, [{'state': 'valid'}])

        # The amount is the same, no message under the 'amount' field.
        self.assert_form_extra_text_value(wizard.form_extra_text, False)

        wizard.button_validate(async_action=False)
        self.assertRecordValues(st_line.line_ids, [
            # pylint: disable=C0326
            {'account_id': st_line.journal_id.default_account_id.id,    'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0,  'reconciled': False},
            {'account_id': inv_line.account_id.id,                      'amount_currency': -4800.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1200.0, 'reconciled': True},
        ])
        self.assertRecordValues(st_line, [{'is_reconciled': True}])
        self.assertRecordValues(inv_line.move_id, [{'payment_state': 'paid'}])

        # Reset the wizard.
        wizard.button_reset()
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0},
            {'flag': 'auto_balance',    'amount_currency': -1200.0,     'currency_id': self.company_data['currency'].id,    'balance': -1200.0},
        ])

        # Create the same invoice with a higher amount to check the partial flow.
        # 7200.0 curr2 == 1200.0 comp_curr (rate 6:1)
        inv_line = self._create_invoice_line(
            'out_invoice',
            currency_id=self.currency_data_2['currency'],
            invoice_date='2016-01-01',
            invoice_line_ids=[{'price_unit': 7200.0}],
        )
        wizard._action_add_new_amls(inv_line)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',   'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0},
            {'flag': 'new_aml',     'amount_currency': -4800.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1200.0},
        ])

        # Check the message under the 'amount' field.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'new_aml')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        wizard = form.save()
        self.assert_form_extra_text_value(
            wizard.form_extra_text,
            r".+open amount of 7,200.000.+ reduced by 4,800.000.+ set the invoice as fully paid .",
        )
        self.assertRecordValues(wizard, [{
            'form_suggest_amount_currency': 7200.0,
            'form_suggest_balance': 1800.0,
        }])

        # Switch to a full reconciliation.
        form = WizardForm(wizard)
        form.todo_command = 'button_clicked,button_form_apply_suggestion'
        wizard = form.save()
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0},
            {'flag': 'new_aml',         'amount_currency': -7200.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1800.0},
            {'flag': 'auto_balance',    'amount_currency': 600.0,       'currency_id': self.company_data['currency'].id,    'balance': 600.0},
        ])

        # Check the message under the 'amount' field.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'new_aml')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        wizard = form.save()
        self.assert_form_extra_text_value(
            wizard.form_extra_text,
            r".+open amount of 7,200.000.+ paid .+ record a partial payment .",
        )
        self.assertRecordValues(wizard, [{
            'form_suggest_amount_currency': 4800.0,
            'form_suggest_balance': 1200.0,
        }])

        # Switch back to a partial reconciliation.
        form = WizardForm(wizard)
        form.todo_command = 'button_clicked,button_form_apply_suggestion'
        wizard = form.save()
        self.assertRecordValues(wizard, [{'state': 'valid'}])

        # Reconcile
        wizard.button_validate(async_action=False)
        self.assertRecordValues(st_line.line_ids, [
            # pylint: disable=C0326
            {'account_id': st_line.journal_id.default_account_id.id,    'amount_currency': 1200.0,      'currency_id': self.company_data['currency'].id,    'balance': 1200.0,  'reconciled': False},
            {'account_id': inv_line.account_id.id,                      'amount_currency': -4800.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1200.0, 'reconciled': True},
        ])
        self.assertRecordValues(st_line, [{'is_reconciled': True}])
        self.assertRecordValues(inv_line.move_id, [{
            'payment_state': 'partial',
            'amount_residual': 2400.0,
        }])

    def test_validation_new_aml_multi_currencies(self):
        # 6300.0 curr2 == 1800.0 comp_curr (bank rate 3.5:1 instead of the odoo rate 4:1)
        st_line = self._create_st_line(
            1800.0,
            date='2017-01-01',
            foreign_currency_id=self.currency_data_2['currency'].id,
            amount_currency=6300.0,
        )
        # 21600.0 curr3 == 1800.0 comp_curr (rate 12:1)
        inv_line = self._create_invoice_line(
            'out_invoice',
            currency_id=self.currency_data_3['currency'],
            invoice_date='2016-01-01',
            invoice_line_ids=[{'price_unit': 21600.0}],
        )

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_amls(inv_line)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',   'amount_currency': 1800.0,      'currency_id': self.company_data['currency'].id,    'balance': 1800.0},
            {'flag': 'new_aml',     'amount_currency': -21600.0,    'currency_id': self.currency_data_3['currency'].id, 'balance': -1800.0},
        ])
        self.assertRecordValues(wizard, [{'state': 'valid'}])

        # The amount is the same, no message under the 'amount' field.
        self.assert_form_extra_text_value(wizard.form_extra_text, False)

        wizard.button_validate(async_action=False)
        self.assertRecordValues(st_line.line_ids, [
            # pylint: disable=C0326
            {'account_id': st_line.journal_id.default_account_id.id,    'amount_currency': 1800.0,      'currency_id': self.company_data['currency'].id,    'balance': 1800.0,  'reconciled': False},
            {'account_id': inv_line.account_id.id,                      'amount_currency': -21600.0,    'currency_id': self.currency_data_3['currency'].id, 'balance': -1800.0, 'reconciled': True},
        ])
        self.assertRecordValues(st_line, [{'is_reconciled': True}])
        self.assertRecordValues(inv_line.move_id, [{'payment_state': 'paid'}])

        # Reset the wizard.
        wizard.button_reset()
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1800.0,      'currency_id': self.company_data['currency'].id,    'balance': 1800.0},
            {'flag': 'auto_balance',    'amount_currency': -6300.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -1800.0},
        ])

        # Create the same invoice with a higher amount to check the partial flow.
        # 32400.0 curr3 == 2700.0 comp_curr (rate 12:1)
        inv_line = self._create_invoice_line(
            'out_invoice',
            currency_id=self.currency_data_3['currency'],
            invoice_date='2016-01-01',
            invoice_line_ids=[{'price_unit': 32400.0}],
        )
        wizard._action_add_new_amls(inv_line)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',   'amount_currency': 1800.0,      'currency_id': self.company_data['currency'].id,    'balance': 1800.0},
            {'flag': 'new_aml',     'amount_currency': -21600.0,    'currency_id': self.currency_data_3['currency'].id, 'balance': -1800.0},
        ])

        # Check the message under the 'amount' field.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'new_aml')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        wizard = form.save()
        self.assert_form_extra_text_value(
            wizard.form_extra_text,
            r".+open amount of 32,400.000.+ reduced by 21,600.000.+ set the invoice as fully paid .",
        )
        self.assertRecordValues(wizard, [{
            'form_suggest_amount_currency': 32400.0,
            'form_suggest_balance': 2700.0,
        }])

        # Switch to a full reconciliation.
        form = WizardForm(wizard)
        form.todo_command = 'button_clicked,button_form_apply_suggestion'
        wizard = form.save()
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1800.0,      'currency_id': self.company_data['currency'].id,    'balance': 1800.0},
            {'flag': 'new_aml',         'amount_currency': -32400.0,    'currency_id': self.currency_data_3['currency'].id, 'balance': -2700.0},
            {'flag': 'auto_balance',    'amount_currency': 3150.0,      'currency_id': self.currency_data_2['currency'].id, 'balance': 900.0},
        ])

        # Check the message under the 'amount' field.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'new_aml')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        wizard = form.save()
        self.assert_form_extra_text_value(
            wizard.form_extra_text,
            r".+open amount of 32,400.000.+ paid .+ record a partial payment .",
        )
        self.assertRecordValues(wizard, [{
            'form_suggest_amount_currency': 21600.0,
            'form_suggest_balance': 1800.0,
        }])

        # Switch back to a partial reconciliation.
        form = WizardForm(wizard)
        form.todo_command = 'button_clicked,button_form_apply_suggestion'
        wizard = form.save()
        self.assertRecordValues(wizard, [{'state': 'valid'}])

        # Reconcile
        wizard.button_validate(async_action=False)
        self.assertRecordValues(st_line.line_ids, [
            # pylint: disable=C0326
            {'account_id': st_line.journal_id.default_account_id.id,    'amount_currency': 1800.0,      'currency_id': self.company_data['currency'].id,    'balance': 1800.0,  'reconciled': False},
            {'account_id': inv_line.account_id.id,                      'amount_currency': -21600.0,    'currency_id': self.currency_data_3['currency'].id, 'balance': -1800.0, 'reconciled': True},
        ])
        self.assertRecordValues(st_line, [{'is_reconciled': True}])
        self.assertRecordValues(inv_line.move_id, [{
            'payment_state': 'partial',
            'amount_residual': 10800.0,
        }])

    def test_validation_with_partner(self):
        partner = self.partner_a.copy()

        st_line = self._create_st_line(1000.0, partner_id=self.partner_a.id)

        # The wizard can be validated directly thanks to the receivable account set on the partner.
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        self.assertRecordValues(wizard, [{'state': 'valid'}])

        # Validate and check the statement line.
        wizard.button_validate(async_action=False)
        liquidity_line, _suspense_line, other_line = st_line._seek_for_lines()
        account = self.partner_a.property_account_receivable_id
        self.assertRecordValues(liquidity_line + other_line, [
            # pylint: disable=C0326
            {'account_id': liquidity_line.account_id.id,    'balance': 1000.0},
            {'account_id': account.id,                      'balance': -1000.0},
        ])
        self.assertRecordValues(wizard, [{'state': 'reconciled'}])

        # Match an invoice with a different partner.
        wizard.button_reset()
        inv_line = self._create_invoice_line(
            'out_invoice',
            partner_id=partner,
            invoice_line_ids=[{'price_unit': 1000.0}],
        )
        wizard._action_add_new_amls(inv_line)
        wizard.button_validate(async_action=False)
        liquidity_line, _suspense_line, other_line = st_line._seek_for_lines()
        self.assertRecordValues(st_line, [{'partner_id': partner.id}])
        self.assertRecordValues(liquidity_line + other_line, [
            # pylint: disable=C0326
            {'account_id': liquidity_line.account_id.id,    'partner_id': partner.id,   'balance': 1000.0},
            {'account_id': inv_line.account_id.id,          'partner_id': partner.id,   'balance': -1000.0},
        ])
        self.assertRecordValues(wizard, [{'state': 'reconciled'}])

        # Reset the wizard and match invoices with different partners.
        wizard.button_reset()
        partner1 = self.partner_a.copy()
        inv_line1 = self._create_invoice_line(
            'out_invoice',
            partner_id=partner1,
            invoice_line_ids=[{'price_unit': 300.0}],
        )
        partner2 = self.partner_a.copy()
        inv_line2 = self._create_invoice_line(
            'out_invoice',
            partner_id=partner2,
            invoice_line_ids=[{'price_unit': 300.0}],
        )
        wizard._action_add_new_amls(inv_line1 + inv_line2)
        wizard.button_validate(async_action=False)
        liquidity_line, _suspense_line, other_line = st_line._seek_for_lines()
        self.assertRecordValues(st_line, [{'partner_id': False}])
        self.assertRecordValues(liquidity_line + other_line, [
            # pylint: disable=C0326
            {'account_id': liquidity_line.account_id.id,    'partner_id': False,        'balance': 1000.0},
            {'account_id': inv_line1.account_id.id,         'partner_id': partner1.id,  'balance': -300.0},
            {'account_id': inv_line2.account_id.id,         'partner_id': partner2.id,  'balance': -300.0},
            {'account_id': account.id,                      'partner_id': False,        'balance': -400.0},
        ])
        self.assertRecordValues(wizard, [{'state': 'reconciled'}])

    def test_validation_using_custom_account(self):
        st_line = self._create_st_line(1000.0)

        # By default, the wizard can't be validated directly due to the suspense account.
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        self.assertRecordValues(wizard, [{'state': 'invalid'}])

        # Mount the auto-balance line in edit mode.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'auto_balance')
        wizard._action_mount_line_in_edit(line.index)
        liquidity_line, suspense_line, _other_lines = st_line._seek_for_lines()
        self.assertRecordValues(wizard, [{
            'form_index': line.index,
            'form_account_id': suspense_line.account_id.id,
            'form_balance': -1000.0,
        }])

        # Switch to a custom account.
        account = self.env['account.account'].create({
            'name': "test_validation_using_custom_account",
            'code': "424242",
            'account_type': "asset_current",
        })
        form = WizardForm(wizard)
        form.form_account_id = account
        wizard = form.save()
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',   'account_id': liquidity_line.account_id.id, 'balance': 1000.0},
            {'flag': 'manual',      'account_id': account.id,                   'balance': -1000.0},
        ])

        # The wizard can be validated.
        self.assertRecordValues(wizard, [{'state': 'valid'}])

        # Validate and check the statement line.
        wizard.button_validate(async_action=False)
        liquidity_line, _suspense_line, other_line = st_line._seek_for_lines()
        self.assertRecordValues(liquidity_line + other_line, [
            # pylint: disable=C0326
            {'account_id': liquidity_line.account_id.id,    'balance': 1000.0},
            {'account_id': account.id,                      'balance': -1000.0},
        ])
        self.assertRecordValues(wizard, [{'state': 'reconciled'}])

    def test_validation_with_taxes(self):
        st_line = self._create_st_line(1000.0)

        tax_tags = self.env['account.account.tag'].create({
            'name': f'tax_tag_{i}',
            'applicability': 'taxes',
            'country_id': self.env.company.account_fiscal_country_id.id,
        } for i in range(4))

        tax_21 = self.env['account.tax'].create({
            'name': "tax_21",
            'amount': 21,
            'invoice_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'tag_ids': [Command.set(tax_tags[0].ids)],
                }),
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'tag_ids': [Command.set(tax_tags[1].ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'tag_ids': [Command.set(tax_tags[2].ids)],
                }),
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'tag_ids': [Command.set(tax_tags[3].ids)],
                }),
            ],
        })

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        line = wizard.line_ids.filtered(lambda x: x.flag == 'auto_balance')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        form.form_tax_ids.add(tax_21)
        wizard = form.save()

        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',   'balance': 1000.0,  'tax_tag_ids': []},
            {'flag': 'manual',      'balance': -826.45, 'tax_tag_ids': tax_tags[0].ids},
            {'flag': 'tax_line',    'balance': -173.55, 'tax_tag_ids': tax_tags[1].ids},
        ])

        # Edit the base line. The tax tags should be the refund ones.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'manual')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        form.form_balance = 500.0
        wizard = form.save()

        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance': 1000.0,      'tax_tag_ids': []},
            {'flag': 'manual',          'balance': 500.0,       'tax_tag_ids': tax_tags[2].ids},
            {'flag': 'tax_line',        'balance': 105.0,       'tax_tag_ids': tax_tags[3].ids},
            {'flag': 'auto_balance',    'balance': -1605.0,     'tax_tag_ids': []},
        ])

        # Edit the base line.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'manual')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        form.form_balance = -500.0
        wizard = form.save()

        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance': 1000.0,  'tax_tag_ids': []},
            {'flag': 'manual',          'balance': -500.0,  'tax_tag_ids': tax_tags[0].ids},
            {'flag': 'tax_line',        'balance': -105.0,  'tax_tag_ids': tax_tags[1].ids},
            {'flag': 'auto_balance',    'balance': -395.0,  'tax_tag_ids': []},
        ])

        # Edit the tax line.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'tax_line')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        form.form_balance = -100.0
        wizard = form.save()

        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance': 1000.0,  'tax_tag_ids': []},
            {'flag': 'manual',          'balance': -500.0,  'tax_tag_ids': tax_tags[0].ids},
            {'flag': 'tax_line',        'balance': -100.0,  'tax_tag_ids': tax_tags[1].ids},
            {'flag': 'auto_balance',    'balance': -400.0,  'tax_tag_ids': []},
        ])

        # Add a new tax.
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount': 10,
        })

        line = wizard.line_ids.filtered(lambda x: x.flag == 'manual')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        form.form_tax_ids.add(tax_10)
        wizard = form.save()

        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance': 1000.0},
            {'flag': 'manual',          'balance': -500.0},
            {'flag': 'tax_line',        'balance': -105.0},
            {'flag': 'tax_line',        'balance': -50.0},
            {'flag': 'auto_balance',    'balance': -345.0},
        ])

        # Remove the taxes.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'manual')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        form.form_tax_ids.clear()
        wizard = form.save()

        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance': 1000.0},
            {'flag': 'manual',          'balance': -500.0},
            {'flag': 'auto_balance',    'balance': -500.0},
        ])

        # Reset the amount.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'manual')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        form.form_balance = -1000.0
        wizard = form.save()

        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance': 1000.0},
            {'flag': 'manual',          'balance': -1000.0},
        ])

        # Add taxes. We should be back into the "price included taxes" mode.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'manual')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        form.form_tax_ids.add(tax_21)
        wizard = form.save()

        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',   'balance': 1000.0},
            {'flag': 'manual',      'balance': -826.45},
            {'flag': 'tax_line',    'balance': -173.55},
        ])

        line = wizard.line_ids.filtered(lambda x: x.flag == 'manual')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        form.form_tax_ids.add(tax_10)
        wizard = form.save()

        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',   'balance': 1000.0},
            {'flag': 'manual',      'balance': -763.36},
            {'flag': 'tax_line',    'balance': -160.31},
            {'flag': 'tax_line',    'balance': -76.33},
        ])

        # Changing the account should recompute the taxes but preserve the "price included taxes" mode.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'manual')
        form = WizardForm(wizard)
        form.todo_command = f'mount_line_in_edit,{line.index}'
        form.form_account_id = self.account_revenue1
        wizard = form.save()

        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',   'balance': 1000.0},
            {'flag': 'manual',      'balance': -763.36},
            {'flag': 'tax_line',    'balance': -160.31},
            {'flag': 'tax_line',    'balance': -76.33},
        ])

        # The wizard can be validated.
        self.assertRecordValues(wizard, [{'state': 'valid'}])

        # Validate and check the statement line.
        wizard.button_validate(async_action=False)
        self.assertRecordValues(st_line.line_ids, [
            # pylint: disable=C0326
            {'balance': 1000.0},
            {'balance': -763.36},
            {'balance': -160.31},
            {'balance': -76.33},
        ])
        self.assertRecordValues(wizard, [{'state': 'reconciled'}])

    def test_apply_taxes_with_reco_model(self):
        st_line = self._create_st_line(1000.0)

        tax_21 = self.env['account.tax'].create({
            'name': "tax_21",
            'amount': 21,
        })

        reco_model = self.env['account.reconcile.model'].create({
            'name': "test_apply_taxes_with_reco_model",
            'rule_type': 'writeoff_button',
            'line_ids': [Command.create({
                'account_id': self.account_revenue1.id,
                'tax_ids': [Command.set(tax_21.ids)],
            })],
        })

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_select_reconcile_model(reco_model)

        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',   'balance': 1000.0},
            {'flag': 'manual',      'balance': -826.45},
            {'flag': 'tax_line',    'balance': -173.55},
        ])

    def test_creating_manual_line_multi_currencies(self):
        # 6300.0 curr2 == 1800.0 comp_curr (bank rate 3.5:1 instead of the odoo rate 4:1)
        st_line = self._create_st_line(
            1800.0,
            date='2017-01-01',
            foreign_currency_id=self.currency_data_2['currency'].id,
            amount_currency=6300.0,
        )

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1800.0,  'currency_id': self.company_data['currency'].id,    'balance': 1800.0},
            {'flag': 'auto_balance',    'amount_currency': -6300.0, 'currency_id': self.currency_data_2['currency'].id, 'balance': -1800.0},
        ])

        # Custom balance.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'auto_balance')
        wizard._action_mount_line_in_edit(line.index)
        form = WizardForm(wizard)
        form.form_balance = -1500.0
        wizard = form.save()
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1800.0,  'currency_id': self.company_data['currency'].id,    'balance': 1800.0},
            {'flag': 'manual',          'amount_currency': -6300.0, 'currency_id': self.currency_data_2['currency'].id, 'balance': -1500.0},
            {'flag': 'auto_balance',    'amount_currency': 0.0,     'currency_id': self.currency_data_2['currency'].id, 'balance': -300.0},
        ])

        # Custom amount_currency.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'manual')
        wizard._action_mount_line_in_edit(line.index)
        form = WizardForm(wizard)
        form.form_amount_currency = -4200.0
        wizard = form.save()
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1800.0,  'currency_id': self.company_data['currency'].id,    'balance': 1800.0},
            {'flag': 'manual',          'amount_currency': -4200.0, 'currency_id': self.currency_data_2['currency'].id, 'balance': -1200.0},
            {'flag': 'auto_balance',    'amount_currency': -2100.0, 'currency_id': self.currency_data_2['currency'].id, 'balance': -600.0},
        ])

        # Custom currency_id.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'manual')
        wizard._action_mount_line_in_edit(line.index)
        form = WizardForm(wizard)
        form.form_currency_id = self.currency_data['currency']
        wizard = form.save()
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1800.0,  'currency_id': self.company_data['currency'].id,    'balance': 1800.0},
            {'flag': 'manual',          'amount_currency': -4200.0, 'currency_id': self.currency_data['currency'].id,   'balance': -2100.0},
            {'flag': 'auto_balance',    'amount_currency': 1050.0,  'currency_id': self.currency_data_2['currency'].id, 'balance': 300.0},
        ])

        # Custom balance.
        line = wizard.line_ids.filtered(lambda x: x.flag == 'manual')
        wizard._action_mount_line_in_edit(line.index)
        form = WizardForm(wizard)
        form.form_balance = -1800.0
        wizard = form.save()
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1800.0,  'currency_id': self.company_data['currency'].id,    'balance': 1800.0},
            {'flag': 'manual',          'amount_currency': -4200.0, 'currency_id': self.currency_data['currency'].id,   'balance': -1800.0},
        ])

    def test_auto_reconcile_cron(self):
        self.env['account.reconcile.model'].search([('company_id', '=', self.company_data['company'].id)]).unlink()

        st_line = self._create_st_line(1234.0, partner_id=self.partner_a.id, date='2017-01-01')
        self._create_invoice_line(
            'out_invoice',
            invoice_date='2017-01-01',
            invoice_line_ids=[{'price_unit': 1234.0}],
        )

        rule = self.env['account.reconcile.model'].create({
            'name': "test_auto_reconcile_cron",
            'rule_type': 'writeoff_suggestion',
            'auto_reconcile': False,
            'line_ids': [Command.create({'account_id': self.account_revenue1.id})],
        })

        # The CRON is not doing anything since the model is not auto reconcile.
        with freeze_time('2017-01-01'):
            self.env['account.bank.statement.line']._cron_try_auto_reconcile_statement_lines()
        self.assertRecordValues(st_line, [{'is_reconciled': False, 'cron_last_check': False}])

        rule.auto_reconcile = True

        # The CRON don't consider old statement lines.
        with freeze_time('2017-06-01'):
            self.env['account.bank.statement.line']._cron_try_auto_reconcile_statement_lines()
        self.assertRecordValues(st_line, [{'is_reconciled': False, 'cron_last_check': False}])

        # The CRON will auto-reconcile the line.
        with freeze_time('2017-01-02'):
            self.env['account.bank.statement.line']._cron_try_auto_reconcile_statement_lines()
        self.assertRecordValues(st_line, [{'is_reconciled': True, 'cron_last_check': fields.Datetime.from_string('2017-01-02 00:00:00')}])

        st_line1 = self._create_st_line(1234.0, partner_id=self.partner_a.id, date='2018-01-01')
        self._create_invoice_line(
            'out_invoice',
            invoice_date='2018-01-01',
            invoice_line_ids=[{'price_unit': 1234.0}],
        )
        st_line2 = self._create_st_line(1234.0, partner_id=self.partner_a.id, date='2018-01-01')
        self._create_invoice_line(
            'out_invoice',
            invoice_date='2018-01-01',
            invoice_line_ids=[{'price_unit': 1234.0}],
        )

        # Simulate the cron already tried to process 'st_line1' before.
        with freeze_time('2017-12-31'):
            st_line1.cron_last_check = fields.Datetime.now()

        # The statement line with no 'cron_last_check' must be processed before others.
        with freeze_time('2018-01-02'):
            self.env['account.bank.statement.line']._cron_try_auto_reconcile_statement_lines(batch_size=1)

        self.assertRecordValues(st_line1 + st_line2, [
            {'is_reconciled': False, 'cron_last_check': fields.Datetime.from_string('2017-12-31 00:00:00')},
            {'is_reconciled': True, 'cron_last_check': fields.Datetime.from_string('2018-01-02 00:00:00')},
        ])

        with freeze_time('2018-01-03'):
            self.env['account.bank.statement.line']._cron_try_auto_reconcile_statement_lines(batch_size=1)

        self.assertRecordValues(st_line1, [{'is_reconciled': True, 'cron_last_check': fields.Datetime.from_string('2018-01-03 00:00:00')}])

    def test_duplicate_amls_constraint(self):
        st_line = self._create_st_line(1000.0)
        inv_line = self._create_invoice_line(
            'out_invoice',
            invoice_line_ids=[{'price_unit': 1000.0}],
        )

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_amls(inv_line)
        wizard._action_add_new_amls(inv_line)

        # Trigger the compute
        with self.assertRaises(UserError), self.cr.savepoint():
            wizard.lines_widget

    @freeze_time('2017-01-01')
    def test_reconcile_model_with_payment_tolerance(self):
        self.env['account.reconcile.model'].search([('company_id', '=', self.company_data['company'].id)]).unlink()

        invoice_line = self._create_invoice_line(
            'out_invoice',
            invoice_date='2017-01-01',
            invoice_line_ids=[{'price_unit': 1000.0}],
        )
        st_line = self._create_st_line(998.0, partner_id=self.partner_a.id, date='2017-01-01', payment_ref=invoice_line.move_id.name)

        rule = self.env['account.reconcile.model'].create({
            'name': "test_reconcile_model_with_payment_tolerance",
            'rule_type': 'invoice_matching',
            'allow_payment_tolerance': True,
            'payment_tolerance_type': 'percentage',
            'payment_tolerance_param': 2.0,
            'line_ids': [Command.create({'account_id': self.account_revenue1.id})],
        })

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        form = WizardForm(wizard)
        form.todo_command = 'trigger_matching_rules'
        wizard = form.save()
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance': 998.0,   'reconcile_model_id': False},
            {'flag': 'new_aml',         'balance': -1000.0, 'reconcile_model_id': rule.id},
            {'flag': 'manual',          'balance': 2.0,     'reconcile_model_id': rule.id},
        ])

    def test_early_payment_included_multi_currency(self):
        self.env['account.reconcile.model'].search([('company_id', '=', self.company_data['company'].id)]).unlink()
        self.env.company.early_pay_discount_computation = 'included'

        inv_line1_with_epd = self._create_invoice_line(
            'out_invoice',
            currency_id=self.currency_data_2['currency'],
            partner_id=self.partner_a,
            invoice_payment_term_id=self.early_payment_term,
            invoice_date='2016-12-01',
            invoice_line_ids=[
                {
                    'price_unit': 4800.0,
                    'account_id': self.account_revenue1,
                    'tax_ids': self.company_data['default_tax_sale'],
                },
                {
                    'price_unit': 9600.0,
                    'account_id': self.account_revenue2,
                    'tax_ids': self.company_data['default_tax_sale'],
                },
            ],
        )
        inv_line1_with_epd_rec_lines = inv_line1_with_epd.move_id.line_ids\
            .filtered(lambda x: x.account_type == 'asset_receivable')\
            .sorted(lambda x: x.discount_date or x.date_maturity)
        self.assertRecordValues(
            inv_line1_with_epd_rec_lines,
            [
                {
                    'amount_currency': 1656.0,
                    'discount_amount_currency': 0.0,
                    'discount_balance': 0.0,
                    'discount_date': False,
                    'date_maturity': fields.Date.from_string('2016-12-06'),
                },
                {
                    'amount_currency': 3312.0,
                    'discount_amount_currency': 3146.4,
                    'discount_balance': 524.4,
                    'discount_date': fields.Date.from_string('2016-12-11'),
                    'date_maturity': fields.Date.from_string('2016-12-21'),
                },
                {
                    'amount_currency': 6624.0,
                    'discount_amount_currency': 5961.6,
                    'discount_balance': 993.6,
                    'discount_date': fields.Date.from_string('2017-01-05'),
                    'date_maturity': fields.Date.from_string('2017-01-10'),
                },
                {
                    'amount_currency': 4968.0,
                    'discount_amount_currency': 0.0,
                    'discount_balance': 0.0,
                    'discount_date': False,
                    'date_maturity': fields.Date.from_string('2017-01-20'),
                },
            ],
        )

        inv_line2_with_epd = self._create_invoice_line(
            'out_invoice',
            currency_id=self.currency_data_2['currency'],
            partner_id=self.partner_a,
            invoice_payment_term_id=self.early_payment_term,
            invoice_date='2017-01-20',
            invoice_line_ids=[
                {
                    'price_unit': 480.0,
                    'account_id': self.account_revenue1,
                    'tax_ids': self.company_data['default_tax_sale'],
                },
                {
                    'price_unit': 960.0,
                    'account_id': self.account_revenue2,
                    'tax_ids': self.company_data['default_tax_sale'],
                },
            ],
        )
        inv_line2_with_epd_rec_lines = inv_line2_with_epd.move_id.line_ids\
            .filtered(lambda x: x.account_type == 'asset_receivable')\
            .sorted(lambda x: x.discount_date or x.date_maturity)
        self.assertRecordValues(
            inv_line2_with_epd_rec_lines,
            [
                {
                    'amount_currency': 165.6,
                    'discount_amount_currency': 0.0,
                    'discount_balance': 0.0,
                    'discount_date': False,
                    'date_maturity': fields.Date.from_string('2017-01-25'),
                },
                {
                    'amount_currency': 331.2,
                    'discount_amount_currency': 314.64,
                    'discount_balance': 78.66,
                    'discount_date': fields.Date.from_string('2017-01-30'),
                    'date_maturity': fields.Date.from_string('2017-02-09'),
                },
                {
                    'amount_currency': 662.4,
                    'discount_amount_currency': 596.16,
                    'discount_balance': 149.04,
                    'discount_date': fields.Date.from_string('2017-02-24'),
                    'date_maturity': fields.Date.from_string('2017-03-01'),
                },
                {
                    'amount_currency': 496.8,
                    'discount_amount_currency': 0.0,
                    'discount_balance': 0.0,
                    'discount_date': False,
                    'date_maturity': fields.Date.from_string('2017-03-11'),
                },
            ],
        )

        # inv1: 1656.0 + 3312.0 + 5961.6 (epd) + 4968.0
        # inv2: 165.6 + 314.64 (epd)
        st_line = self._create_st_line(
            4095.0, # instead of 4094.46 (rate 1:4)
            date='2017-01-04',
            foreign_currency_id=self.currency_data_2['currency'].id,
            amount_currency=16377.84,
        )

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})

        # Add all lines from the first invoice plus the first one from the second one.
        wizard._action_add_new_amls(inv_line1_with_epd_rec_lines + inv_line2_with_epd_rec_lines[0])
        liquidity_acc = st_line.journal_id.default_account_id
        receivable_acc = self.company_data['default_account_receivable']
        suspense_acc = self.env.company.account_journal_suspense_account_id
        early_pay_acc = self.env.company.account_journal_early_pay_discount_loss_account_id
        tax_acc = self.company_data['default_tax_sale'].invoice_repartition_line_ids.account_id
        foreign_exch_acc = self.env.company.expense_currency_exchange_account_id
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 4095.0,      'balance': 4095.0,      'account_id': liquidity_acc.id},
            {'flag': 'new_aml',         'amount_currency': -1656.0,     'balance': -414.05,     'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -3312.0,     'balance': -828.11,     'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -6624.0,     'balance': -1656.22,    'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -4968.0,     'balance': -1242.16,    'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -165.6,      'balance': -41.41,      'account_id': receivable_acc.id},
            {'flag': 'auto_balance',    'amount_currency': 347.76,      'balance': 86.95,       'account_id': suspense_acc.id},
        ])

        # Add the last missing line to reach the early payment matching.
        wizard._action_add_new_amls(inv_line2_with_epd_rec_lines[1])
        expected_values_list = [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 4095.0,      'balance': 4095.0,      'account_id': liquidity_acc.id},
            {'flag': 'new_aml',         'amount_currency': -1656.0,     'balance': -414.05,     'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -3312.0,     'balance': -828.11,     'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -6624.0,     'balance': -1656.22,    'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -4968.0,     'balance': -1242.16,    'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -165.6,      'balance': -41.41,      'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -331.2,      'balance': -82.81,      'account_id': receivable_acc.id},
            {'flag': 'early_payment',   'amount_currency': 590.4,       'balance': 99.6,        'account_id': early_pay_acc.id},
            {'flag': 'early_payment',   'amount_currency': 88.56,       'balance': 14.94,       'account_id': tax_acc.id},
            {'flag': 'early_payment',   'amount_currency': 0.0,         'balance': 55.22,       'account_id': foreign_exch_acc.id},
        ]
        self.assertRecordValues(wizard.line_ids, expected_values_list)

    def test_early_payment_excluded_multi_currency(self):
        self.env['account.reconcile.model'].search([('company_id', '=', self.company_data['company'].id)]).unlink()
        self.env.company.early_pay_discount_computation = 'excluded'

        inv_line1_with_epd = self._create_invoice_line(
            'out_invoice',
            currency_id=self.currency_data_2['currency'],
            partner_id=self.partner_a,
            invoice_payment_term_id=self.early_payment_term,
            invoice_date='2016-12-01',
            invoice_line_ids=[
                {
                    'price_unit': 4800.0,
                    'account_id': self.account_revenue1,
                    'tax_ids': self.company_data['default_tax_sale'],
                },
                {
                    'price_unit': 9600.0,
                    'account_id': self.account_revenue2,
                    'tax_ids': self.company_data['default_tax_sale'],
                },
            ],
        )
        inv_line1_with_epd_rec_lines = inv_line1_with_epd.move_id.line_ids\
            .filtered(lambda x: x.account_type == 'asset_receivable')\
            .sorted(lambda x: x.discount_date or x.date_maturity)
        self.assertRecordValues(
            inv_line1_with_epd_rec_lines,
            [
                {
                    'amount_currency': 1656.0,
                    'discount_amount_currency': 0.0,
                    'discount_balance': 0.0,
                    'discount_date': False,
                    'date_maturity': fields.Date.from_string('2016-12-06'),
                },
                {
                    'amount_currency': 3312.0,
                    'discount_amount_currency': 3168.0,
                    'discount_balance': 528.0,
                    'discount_date': fields.Date.from_string('2016-12-11'),
                    'date_maturity': fields.Date.from_string('2016-12-21'),
                },
                {
                    'amount_currency': 6624.0,
                    'discount_amount_currency': 6048.0,
                    'discount_balance': 1008.0,
                    'discount_date': fields.Date.from_string('2017-01-05'),
                    'date_maturity': fields.Date.from_string('2017-01-10'),
                },
                {
                    'amount_currency': 4968.0,
                    'discount_amount_currency': 0.0,
                    'discount_balance': 0.0,
                    'discount_date': False,
                    'date_maturity': fields.Date.from_string('2017-01-20'),
                },
            ],
        )

        inv_line2_with_epd = self._create_invoice_line(
            'out_invoice',
            currency_id=self.currency_data_2['currency'],
            partner_id=self.partner_a,
            invoice_payment_term_id=self.early_payment_term,
            invoice_date='2017-01-20',
            invoice_line_ids=[
                {
                    'price_unit': 480.0,
                    'account_id': self.account_revenue1,
                    'tax_ids': self.company_data['default_tax_sale'],
                },
                {
                    'price_unit': 960.0,
                    'account_id': self.account_revenue2,
                    'tax_ids': self.company_data['default_tax_sale'],
                },
            ],
        )
        inv_line2_with_epd_rec_lines = inv_line2_with_epd.move_id.line_ids\
            .filtered(lambda x: x.account_type == 'asset_receivable')\
            .sorted(lambda x: x.discount_date or x.date_maturity)
        self.assertRecordValues(
            inv_line2_with_epd_rec_lines,
            [
                {
                    'amount_currency': 165.6,
                    'discount_amount_currency': 0.0,
                    'discount_balance': 0.0,
                    'discount_date': False,
                    'date_maturity': fields.Date.from_string('2017-01-25'),
                },
                {
                    'amount_currency': 331.2,
                    'discount_amount_currency': 316.8,
                    'discount_balance': 79.2,
                    'discount_date': fields.Date.from_string('2017-01-30'),
                    'date_maturity': fields.Date.from_string('2017-02-09'),
                },
                {
                    'amount_currency': 662.4,
                    'discount_amount_currency': 604.8,
                    'discount_balance': 151.2,
                    'discount_date': fields.Date.from_string('2017-02-24'),
                    'date_maturity': fields.Date.from_string('2017-03-01'),
                },
                {
                    'amount_currency': 496.8,
                    'discount_amount_currency': 0.0,
                    'discount_balance': 0.0,
                    'discount_date': False,
                    'date_maturity': fields.Date.from_string('2017-03-11'),
                },
            ],
        )

        # inv1: 1656.0 + 3312.0 + 6048.0 (epd) + 4968.0
        # inv2: 165.6 + 316.8 (epd)
        st_line = self._create_st_line(
            4110.0, # instead of 4116.6 (rate 1:4)
            date='2017-01-04',
            foreign_currency_id=self.currency_data_2['currency'].id,
            amount_currency=16466.4,
        )

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})

        # Add all lines from the first invoice plus the first one from the second one.
        wizard._action_add_new_amls(inv_line1_with_epd_rec_lines + inv_line2_with_epd_rec_lines[:2])
        liquidity_acc = st_line.journal_id.default_account_id
        receivable_acc = self.company_data['default_account_receivable']
        early_pay_acc = self.env.company.account_journal_early_pay_discount_loss_account_id
        foreign_exch_acc = self.env.company.expense_currency_exchange_account_id
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 4110.0,      'balance': 4110.0,      'account_id': liquidity_acc.id},
            {'flag': 'new_aml',         'amount_currency': -1656.0,     'balance': -413.34,     'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -3312.0,     'balance': -826.67,     'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -6624.0,     'balance': -1653.34,    'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -4968.0,     'balance': -1240.01,    'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -165.6,      'balance': -41.33,      'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -331.2,      'balance': -82.67,      'account_id': receivable_acc.id},
            {'flag': 'early_payment',   'amount_currency': 590.4,       'balance': 99.6,        'account_id': early_pay_acc.id},
            {'flag': 'early_payment',   'amount_currency': 0.0,         'balance': 47.76,       'account_id': foreign_exch_acc.id},
        ])

    def test_early_payment_mixed_multi_currency(self):
        self.env['account.reconcile.model'].search([('company_id', '=', self.company_data['company'].id)]).unlink()
        self.env.company.early_pay_discount_computation = 'mixed'

        inv_line1_with_epd = self._create_invoice_line(
            'out_invoice',
            currency_id=self.currency_data_2['currency'],
            partner_id=self.partner_a,
            invoice_payment_term_id=self.early_payment_term,
            invoice_date='2016-12-01',
            invoice_line_ids=[
                {
                    'price_unit': 4800.0,
                    'account_id': self.account_revenue1,
                    'tax_ids': self.company_data['default_tax_sale'],
                },
                {
                    'price_unit': 9600.0,
                    'account_id': self.account_revenue2,
                    'tax_ids': self.company_data['default_tax_sale'],
                },
            ],
        )
        inv_line1_with_epd_rec_lines = inv_line1_with_epd.move_id.line_ids\
            .filtered(lambda x: x.account_type == 'asset_receivable')\
            .sorted(lambda x: x.discount_date or x.date_maturity)
        self.assertRecordValues(
            inv_line1_with_epd_rec_lines,
            [
                {
                    'amount_currency': 1645.2,
                    'discount_amount_currency': 0.0,
                    'discount_balance': 0.0,
                    'discount_date': False,
                    'date_maturity': fields.Date.from_string('2016-12-06'),
                },
                {
                    'amount_currency': 3290.4,
                    'discount_amount_currency': 3146.4,
                    'discount_balance': 524.4,
                    'discount_date': fields.Date.from_string('2016-12-11'),
                    'date_maturity': fields.Date.from_string('2016-12-21'),
                },
                {
                    'amount_currency': 6580.8,
                    'discount_amount_currency': 6004.8,
                    'discount_balance': 1000.8,
                    'discount_date': fields.Date.from_string('2017-01-05'),
                    'date_maturity': fields.Date.from_string('2017-01-10'),
                },
                {
                    'amount_currency': 4935.6,
                    'discount_amount_currency': 0.0,
                    'discount_balance': 0.0,
                    'discount_date': False,
                    'date_maturity': fields.Date.from_string('2017-01-20'),
                },
            ],
        )

        inv_line2_with_epd = self._create_invoice_line(
            'out_invoice',
            currency_id=self.currency_data_2['currency'],
            partner_id=self.partner_a,
            invoice_payment_term_id=self.early_payment_term,
            invoice_date='2017-01-20',
            invoice_line_ids=[
                {
                    'price_unit': 480.0,
                    'account_id': self.account_revenue1,
                    'tax_ids': self.company_data['default_tax_sale'],
                },
                {
                    'price_unit': 960.0,
                    'account_id': self.account_revenue2,
                    'tax_ids': self.company_data['default_tax_sale'],
                },
            ],
        )
        inv_line2_with_epd_rec_lines = inv_line2_with_epd.move_id.line_ids\
            .filtered(lambda x: x.account_type == 'asset_receivable')\
            .sorted(lambda x: x.discount_date or x.date_maturity)
        self.assertRecordValues(
            inv_line2_with_epd_rec_lines,
            [
                {
                    'amount_currency': 164.52,
                    'discount_amount_currency': 0.0,
                    'discount_balance': 0.0,
                    'discount_date': False,
                    'date_maturity': fields.Date.from_string('2017-01-25'),
                },
                {
                    'amount_currency': 329.04,
                    'discount_amount_currency': 314.64,
                    'discount_balance': 78.66,
                    'discount_date': fields.Date.from_string('2017-01-30'),
                    'date_maturity': fields.Date.from_string('2017-02-09'),
                },
                {
                    'amount_currency': 658.08,
                    'discount_amount_currency': 600.48,
                    'discount_balance': 150.12,
                    'discount_date': fields.Date.from_string('2017-02-24'),
                    'date_maturity': fields.Date.from_string('2017-03-01'),
                },
                {
                    'amount_currency': 493.56,
                    'discount_amount_currency': 0.0,
                    'discount_balance': 0.0,
                    'discount_date': False,
                    'date_maturity': fields.Date.from_string('2017-03-11'),
                },
            ],
        )

        # inv1: 1645.2 + 3290.4 + 6004.8 (epd) + 4935.6
        # inv2: 164.52 + 314.64 (epd)
        st_line = self._create_st_line(
            4088.79, # instead of 4033.17 (rate 1:4)
            date='2017-01-04',
            foreign_currency_id=self.currency_data_2['currency'].id,
            amount_currency=16355.16,
        )

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})

        # Add all lines from the first invoice plus the first one from the second one.
        wizard._action_add_new_amls(inv_line1_with_epd_rec_lines + inv_line2_with_epd_rec_lines[:2])
        liquidity_acc = st_line.journal_id.default_account_id
        receivable_acc = self.company_data['default_account_receivable']
        early_pay_acc = self.env.company.account_journal_early_pay_discount_loss_account_id
        foreign_exch_acc = self.env.company.expense_currency_exchange_account_id
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 4088.79,     'balance': 4088.79,    'account_id': liquidity_acc.id},
            {'flag': 'new_aml',         'amount_currency': -1645.2,     'balance': -411.3,     'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -3290.4,     'balance': -822.6,     'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -6580.8,     'balance': -1645.2,    'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -4935.6,     'balance': -1233.9,    'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -164.52,     'balance': -41.13,     'account_id': receivable_acc.id},
            {'flag': 'new_aml',         'amount_currency': -329.04,     'balance': -82.26,     'account_id': receivable_acc.id},
            {'flag': 'early_payment',   'amount_currency': 590.40,      'balance': 99.6,       'account_id': early_pay_acc.id},
            {'flag': 'early_payment',   'amount_currency': 0.0,         'balance': 48.00,      'account_id': foreign_exch_acc.id},
        ])
