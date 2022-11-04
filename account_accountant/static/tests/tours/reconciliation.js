odoo.define('account.tour_bank_statement_reconciliation', function(require) {
'use strict';

var Tour = require('web_tour.tour');

Tour.register('bank_statement_reconciliation', {
        test: true,
        // Go to the reconciliation page of the statement: "BNK/2014/001"
    }, [
        // The first line, 'line1' (350.0) should automatically have been
        // reconciled with with 'out_invoice_1' (100.0) and 'out_invoice_2' (250.0).

        // 'line2' should be matched for partial reconciliation with 'in_invoice_1' (-1175.0).

        {
            content: "Open the receivable/payable tab for 'line2'",
            extra_trigger: '.o_reconciliation_line:first[data-mode="inactive"]',
            trigger: '.o_reconciliation_line:nth-child(1) .cell_label:contains("line2")',
        },
        {
            content: "Check the line has been added to the propositions",
            trigger: '.o_reconciliation_line:nth-child(1) .accounting_view .line_amount:contains("500.00")',
        },
        {
            content: "Reconcile 'line2' with 'in_invoice_1'",
            trigger: '.o_reconciliation_line:nth-child(1) .o_reconcile:visible',
        },

        // Reconciliation of 'line3' (-180.0) having no partner.
        // Set 'partner_b', then reconcile with 'in_invoice_2' (-180.0).

        {
            content: "Open the receivable/payable tab for 'line3'",
            extra_trigger: '.o_reconciliation_line:first[data-mode="match_rp"]',
            trigger: '.o_reconciliation_line:nth-child(1) .cell_label:contains("line3")',
            run: 'click',
        },
        {
            content: "Search 'partner_b'",
            extra_trigger: '.o_reconciliation_line:nth-child(1)[data-mode="match_rp"]',
            trigger: '.o_reconciliation_line:nth-child(1) .o_field_many2one[name="partner_id"] input',
            run: 'text partner_b'
        },
        {
            content: "Select 'partner_b' ",
            extra_trigger: '.ui-autocomplete:visible li:eq(1):contains(Create)',
            trigger: '.ui-autocomplete:visible li:contains("partner_b")',
        },
        {
            content: "Open the receivable/payable tab for 'line3'",
            extra_trigger: '.o_reconciliation_line:first[data-mode="match_rp"]',
            trigger: '.o_reconciliation_line:nth-child(1) .cell_label:contains("line3")'
        },
        {
            content: "Search for 'in_invoice_2'",
            extra_trigger: '.o_reconciliation_line:nth-child(1) .match .cell_label:contains("BILL"):not(:contains("partner_b"))',
            trigger: '.o_reconciliation_line:nth-child(1) .match .match_controls .filter',
            run: 'text 180'
        },
        {
            content: "Select the line corresponding to 'in_invoice_2'",
            extra_trigger: '.o_reconciliation_line:nth-child(1) .match tr:only-child',
            trigger: '.o_reconciliation_line:nth-child(1) .o_notebook .cell_left:contains("180.00")'
        },
        {
            content: "Reconcile 'line3' with 'in_invoice_2'",
            trigger: '.o_reconciliation_line:nth-child(1) .o_reconcile:visible',
        },

        // Reconciliation of 'line4' (900.0).
        // Create a write-off line manually.

        {
            content: "Open the manual tab for 'line4'",
            extra_trigger: '.o_reconciliation_line:nth-child(1) .cell_label:contains("line4")',
            trigger: '.o_reconciliation_line:nth-child(1) .o_notebook .nav-link[href*="notebook_page_create"]'
        },
        {
            content: "Enter the write-off account",
            trigger: '.o_reconciliation_line:nth-child(1) .o_field_many2one[name="account_id"] input',
            run: 'text 151000'
        },
        {
            content: "Select the first matched account",
            trigger: '.ui-autocomplete:visible li:last:contains(151000)',
        },
        {
            content: "Reconcile 'line4'",
            trigger: '.o_reconciliation_line:nth-child(1) .o_reconcile:visible',
        },
    ]
);

});
