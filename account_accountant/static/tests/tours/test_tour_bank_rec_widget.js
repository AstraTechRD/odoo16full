/** @odoo-module **/

import tour from 'web_tour.tour';


tour.register('account_accountant_bank_rec_widget',
    {
        test: true,
        url: '/web',
    },
    [
        tour.stepUtils.showAppsMenuItem(),
        ...tour.stepUtils.goToAppSteps('account_accountant.menu_accounting', "Open the accounting module"),

        // Open the widget. The first line should be selected by default.
        {
            content: "Open the bank reconciliation widget",
            extra_trigger: ".breadcrumb",
            trigger: "button.btn-primary[name='action_open_reconcile']",
        },
        {
            content: "The 'line1' should be selected by default",
            extra_trigger: "div[name='lines_widget']",
            trigger: "div[name='lines_widget'] td[field='name']:contains('line1')",
            run: function() {},
        },

        // Test 1: Check the loading of lazy notebook tabs.
        // Check 'amls_tab' (active by default).
        {
            content: "The 'amls_tab' should be active and the inner list view loaded",
            extra_trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table",
            trigger: "a.active[name='amls_tab']",
            run: function() {},
        },
        // Check 'discuss_tab'.
        {
            content: "Click on the 'discuss_tab'",
            extra_trigger: "a.active[name='amls_tab']",
            trigger: "a[name='discuss_tab']",
        },
        {
            content: "The 'discuss_tab' should be active and the chatter loaded",
            extra_trigger: "a.active[name='discuss_tab']",
            trigger: "div.bank_rec_widget_form_discuss_anchor div.o_ChatterContainer",
            run: function() {},
        },
        // Check 'manual_operations_tab'.
        {
            content: "Click on the 'auto_balance' to make the 'manual_operations_tab' visible",
            extra_trigger: "tr.o_bank_rec_auto_balance_line",
            trigger: "tr.o_bank_rec_auto_balance_line td[field='name']",
        },
        {
            content: "The 'manual_operations_tab' should be active",
            trigger: "a.active[name='manual_operations_tab']",
            run: function() {},
        },
        {
            content: "The 'form_name' field should be focus automatically",
            trigger: "div.tab-pane.active input[id='form_name']:focus",
            run: function() {},
        },
        {
            content: "Click on the 'credit' field to change the focus from 'form_name' to 'form_balance'",
            extra_trigger: "tr.o_bank_rec_auto_balance_line",
            trigger: "tr.o_bank_rec_auto_balance_line td[field='credit']",
        },
        {
            content: "Wait to avoid non-deterministic errors on the next step",
            trigger: "tr.o_bank_rec_auto_balance_line td[field='credit']",
            run: function() {},
        },
        {
            content: "The 'form_balance' field should be focus now",
            trigger: "div.tab-pane.active input[id='form_balance']:focus",
            run: function() {},
        },

        // Test 2: Test validation + auto select the next line.
        {
            content: "Click on the 'amls_tab'",
            extra_trigger: "a.active[name='manual_operations_tab']",
            trigger: "a[name='amls_tab']",
        },
        {
            content: "Mount INV/2019/00002",
            extra_trigger: "a.active[name='amls_tab']",
            trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table td[name='move_id']:contains('INV/2019/00002')",
        },
        {
            content: "Check INV/2019/00002 is well marked as selected",
            extra_trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00002')",
            trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00002')",
            run: function() {},
        },
        {
            content: "Remove INV/2019/00002",
            extra_trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00002')",
            trigger: "tr td.o_list_record_remove button",
        },
        {
            content: "Mount INV/2019/00001",
            extra_trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr:not(.o_rec_widget_list_selected_item) td[name='move_id']:contains('INV/2019/00002')",
            trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table td[name='move_id']:contains('INV/2019/00001')",
        },
        {
            content: "Validate",
            extra_trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00001')",
            trigger: "button[name='button_validate']",
        },
        {
            content: "The 'line2' is the next not already reconciled line",
            extra_trigger: "div[name='lines_widget'] td[field='name']:contains('line2')",
            trigger: "div[name='lines_widget'] td[field='name']:contains('line2')",
            run: function() {},
        },

        // Test 3: Test manual operations tab.
        {
            content: "Click on 'credit'",
            trigger: "div[name='lines_widget'] td[field='credit']:last",
        },
        {
            content: "The 'manual_operations_tab' should be active now and the auto_balance line mounted in edit",
            trigger: "a.active[name='manual_operations_tab']",
            run: function() {},
        },
        {
            content: "The last line should be selected",
            trigger: "div[name='lines_widget'] tr.o_bank_rec_selected_line",
            run: function() {},
        },
        {
            content: "Search for 'partner_a'",
            trigger: "div[name='form_partner_id'] input",
            run: "text partner_a",
        },
        {
            content: "Select 'partner_a'",
            extra_trigger: ".ui-autocomplete .o_m2o_dropdown_option a:contains('Create')",
            trigger: ".ui-autocomplete:visible li:contains('partner_a')",
        },
        {
            content: "Select the payable account",
            extra_trigger: "tr:not(.o_bank_rec_auto_balance_line) td[field='partner_id']:contains('partner_a')",
            trigger: "button[name='button_form_partner_payable']",
        },
        {
            content: "Enter a tax",
            extra_trigger: "tr:not(.o_bank_rec_auto_balance_line) td[field='account_id']:contains('Payable')",
            trigger: "div[name='form_tax_ids'] input",
            run: "text 15",
        },
        {
            content: "Select 'Tax 15% (Sales)'",
            extra_trigger: ".ui-autocomplete",
            trigger: ".ui-autocomplete:visible li:contains('Sales')",
        },
        {
            content: "Validate",
            extra_trigger: "div[name='lines_widget'] td[field='tax_ids']",
            trigger: "button[name='button_validate']",
        },
        {
            content: "The 'line3' is the next not already reconciled line",
            trigger: "div[name='lines_widget'] td[field='name']:contains('line3')",
            run: function() {},
        },
        tour.stepUtils.toggleHomeMenu(),
        ...tour.stepUtils.goToAppSteps(
            'account_accountant.menu_accounting',
            "Reset back to accounting module"
        ),
        {
            content: "check that we're back on the dashboard",
            trigger: 'a:contains("Customer Invoices")',
            run() {}
        }
    ]
);
