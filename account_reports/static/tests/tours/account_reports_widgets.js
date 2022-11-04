odoo.define('account_reports_widgets.tour', function (require) {
"use strict";

var tour = require('web_tour.tour');

tour.register('account_reports_widgets', {
    test: true,
    url: '/web?#action=account_reports.action_account_report_pl',
},
    [
        {
            content: "wait web client",
            trigger: ".o_account_reports_body",
            extra_trigger: ".breadcrumb",
            run: function () {}
        },
        {
            content: "unfold line",
            trigger: '.js_account_report_foldable:first',
            extra_trigger: '.js_account_report_foldable:first',
            run: 'click',
        },
        {
            content: "check that line has been unfolded",
            trigger: '[data-parent-id]',
            extra_trigger: '[data-parent-id]',
        },
        {
            content: 'Open dropdown menu of one of the unfolded line',
            trigger: '[data-parent-id] .o_account_report_line .dropdown a span',
            extra_trigger: '[data-parent-id] .o_account_report_line .dropdown a span',
            run: 'click',
        },
        {
            content: 'click on the annotate action',
            trigger: '[data-parent-id] .o_account_report_line .dropdown .o_account_reports_domain_dropdown .js_account_reports_add_footnote',
            extra_trigger: '[data-parent-id] .o_account_report_line .dropdown .o_account_reports_domain_dropdown .js_account_reports_add_footnote',
            run: 'click',
        },
        {
            content: 'insert footnote text',
            trigger: '.js_account_reports_footnote_note',
            extra_trigger: '.js_account_reports_footnote_note',
            run: 'text My awesome footnote!'
        },
        {
            content: 'save footnote',
            trigger: '.modal-footer .btn-primary',
            extra_trigger: '.modal-footer .btn-primary',
            run: 'click'
        },
        {
            content: 'wait for footnote to be saved',
            trigger: '.footnote#footnote1 .text:contains(1. My awesome footnote!)',
            extra_trigger: '.o_account_reports_footnote_sup a[href="#footnote1"]',
            run: function(){},
        },
        {
            content: "change date filter",
            trigger: ".o_account_reports_filter_date > button",
            extra_trigger: ".o_account_reports_filter_date > button",
        },
        {
            content: "change date filter",
            trigger: ".o_account_reports_filter_date .dropdown-item.js_account_report_date_filter[data-filter='last_year']",
            extra_trigger: ".o_account_reports_filter_date > button.show",
            run: 'click'
        },
        {
            content: "wait refresh",
            trigger: ".o_account_reports_header_hierarchy th:contains('2019')",
            run: function(){},
        },
        {
            content: "change comparison filter",
            trigger: ".o_account_reports_filter_date_cmp > button",
        },
        {
            content: "change comparison filter",
            trigger: ".dropdown-item.js_foldable_trigger[data-filter='previous_period']",
            extra_trigger: ".o_account_reports_filter_date_cmp > button.show",
        },
        {
            content: "wait for Apply button and click on it",
            trigger: ".js_account_report_date_cmp_filter[data-filter='previous_period']",
            run: 'click',
        },
        {
            content: "wait refresh, report should have 4 columns",
            trigger: "th + th + th + th",
            run: function(){},
        },
        {
            title: "export xlsx",
            trigger: 'button[action_param="export_to_xlsx"]',
            extra_trigger: 'button[action_param="export_to_xlsx"]',
            run: 'click'
        },
    ]
);

});
