/** @odoo-module **/

import tour from 'web_tour.tour';
import tourUtils from 'website_sale.tour_utils';

tour.register('shop_buy_rental_stock_product', {
    test: true,
    url: '/shop',
},
    [
        {
            content: "Search computer write text",
            trigger: 'form input[name="search"]',
            run: "text computer",
        },
        {
            content: "Search computer click",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
        },
        {
            content: "Select computer",
            trigger: '.oe_product_cart:first a:contains("Computer")',
        },
        {
            content: "Open daterangepicker",
            trigger: '#rentingDates [data-toggle="daterange"]',
        },
        {
            content: "Change hours",
            extra_trigger: '.daterangepicker.o_website_sale_renting',
            trigger: '#rentingDates input',
            run: function () {
                const daterangepicker = this.$anchor.data('daterangepicker');
                daterangepicker.setEndDate(daterangepicker.endDate.add(3, 'hours'));
            }
        },
        {
            content: "Apply change",
            trigger: '.daterangepicker.o_website_sale_renting button.applyBtn',
        },
        {
            content: "Add one quantity",
            trigger: '.css_quantity a.js_add_cart_json i.fa-plus',
        },
        {
            content: "click on add to cart",
            trigger: '#product_detail form[action^="/shop/cart/update"] #add_to_cart',
        },
        tourUtils.goToCart({quantity: 2}),
        {
            content: "Verify there is a Computer",
            trigger: '#cart_products tbody td.td-product_name a strong:contains("Computer")',
            run: function () {}, // it's a check
        },
        {
            content: "Verify there are 2 quantity of Computers",
            trigger: '#cart_products tbody td.td-qty div.css_quantity input[value=2]',
            run: function () {}, // it's a check
        },
        {
            content: "Go back on the Computer",
            trigger: '#cart_products tbody td.td-product_name a strong:contains("Computer")',
        },
        {
            content: "Verify there is a warning message",
            trigger: 'div#threshold_message_renting:contains("Only 3 Units still available during the selected period.")',
            run: function () {}, // it's a check
        },
        tourUtils.goToCart({quantity: 2}),
        {
            content: "Check quantity",
            trigger: '#cart_products input.js_quantity:propValue(2)',
            run: function () {}, // it's a check,
        },
        {
            content: "go to checkout",
            extra_trigger: '#cart_products .oe_currency_value:contains(14.00)',
            trigger: 'a[href*="/shop/checkout"]',
        },
        {
            content: "select payment",
            trigger: '#payment_method label:contains("Wire Transfer")',
        },
        {
            content: "Pay Now",
            //Either there are multiple payment methods, and one is checked, either there is only one, and therefore there are no radio inputs
            extra_trigger: '#payment_method label:contains("Wire Transfer") input:checked,#payment_method:not(:has("input:radio:visible"))',
            trigger: 'button[name="o_payment_submit_button"]:visible:not(:disabled)',
        },
        {
            content: "finish",
            trigger: '.oe_website_sale:contains("Please use the following transfer details")',
            // Leave /shop/confirmation to prevent RPC loop to /shop/payment/get_status.
            // The RPC could be handled in python while the tour is killed (and the session), leading to crashes
            run: function () {
                window.location.href = '/contactus'; // Redirect in JS to avoid the RPC loop (20x1sec)
            },
            timeout: 30000,
        },
        {
            content: "wait page loaded",
            trigger: 'h1:contains("Contact us")',
            run: function () {}, // it's a check
        },
    ]
);
