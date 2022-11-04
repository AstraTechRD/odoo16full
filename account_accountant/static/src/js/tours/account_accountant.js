odoo.define('account_accountant.tour', function (require) {
    "use strict";

    const core = require('web.core');
    const {Markup} = require('web.utils');
    const tour = require('web_tour.tour');

    const _t = core._t;
    const { markup } = owl;

    // Update the invoicing tour as the menu items have changed, but we want the test to still work
    tour.tours.account_tour.steps.splice(0, 3,
        ..._.map(tour.stepUtils.goToAppSteps('account_accountant.menu_accounting', _t('Go to invoicing')), step => _.extend(step, {auto: true})),
        {
            trigger: 'button[data-menu-xmlid="account.menu_finance_receivables"]',
            content: _t('Go to invoicing'),
            auto: true,
        }, {
            trigger: '.dropdown-item[data-menu-xmlid="account.menu_action_move_out_invoice_type"]',
            content: _t('Go to invoicing'),
            auto: true,
        }
    )

    tour.register('account_accountant_tour', {
            rainbowManMessage: function() {
                var message = _t('<strong><b>Good job!</b> You went through all steps of this tour.</strong>');
                if (!tour._isTourConsumed('account_tour')) {
                    message += _t('<br>See how to manage your customer invoices in the <b>Customers/Invoices</b> menu');
                }
                return markup(message);
            },
            url: "/web",
            sequence: 50,
        },
        [
            ...tour.stepUtils.goToAppSteps('account_accountant.menu_accounting', _t('Let’s automate your bills, bank transactions and accounting processes.')),
            // The tour will stop here if there is at least 1 vendor bill in the database.
            // While not ideal, it is ok, since that means the user obviously knows how to create a vendor bill...
            {
                trigger: 'button.btn-primary[data-name="action_create_vendor_bill"]',
                content: Markup(_t('Create your first vendor bill.<br/><br/><i>Tip: If you don’t have one on hand, use our sample bill.</i>')),
                position: 'bottom',
            }, {
                trigger: 'button[name="apply"]',
                content: _t('Great! Let’s continue.'),
                position: 'top',
            }, {
                trigger: '.o_data_cell',
                extra_trigger: 'tr:not(.o_sample_data_disabled)>td:has(span[name="payment_state"])',
                content: _t('Let’s see how a bill looks like in form view.'),
                position: 'bottom',
            }, {
                trigger: 'button.btn-primary[name="action_post"]',
                extra_trigger: 'body:has(div[name="waiting_extraction"].o_invisible_modifier)',
                content: _t('Check & validate the bill. If no vendor has been found, add one before validating.'),
                position: 'bottom',
            }, {
                trigger: '.dropdown-item[data-menu-xmlid="account.menu_board_journal_1"]',
                extra_trigger: 'button[data-value="posted"].btn-primary',
                content: _t('Let’s go back to the dashboard.'),
                position: 'bottom',
            }, {
                trigger: 'a[data-method="setting_init_bank_account_action"].o_onboarding_step_action',
                content: _t('Connect your bank and get your latest transactions.'),
                position: 'bottom',
                run: function () {
                    // Close the modal
                    // We can't test bank sync in the tour
                    tour.tours.account_accountant_tour.current_step += 3
                    $('.js_cancel').click();
                }
            }, {
                trigger: 'button[data-name="action_open_reconcile"]',
                content: _t('Let’s reconcile the fetched bank transactions.'),
            }, {
                trigger: '.o_reconciliation_lines .accounting_view button:visible',
                content: _t('Process this transaction.')
            }, {
                trigger: '.breadcrumb-item:not(.active):first',
                content: _t('Get back to the dashboard using your previous path…'),
                position: 'bottom',
            }
        ]
    );

    tour.register('account_accountant_tour_upload_ocr_step', {
            rainbowMan: false,
            sequence: 70,
        },
        [
            {
                trigger: 'button.btn-primary[name="check_status"]',
                content: Markup(_t('Let’s use AI to fill in the form<br/><br/><i>Tip: If the OCR is not done yet, wait a few more seconds and try again.</i>')),
                position: 'bottom',
            }
        ]
    )
});
