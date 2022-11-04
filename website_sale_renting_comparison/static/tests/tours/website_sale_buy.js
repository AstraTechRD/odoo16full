/** @odoo-module **/

import tour from 'web_tour.tour';
import tourUtils from 'website_sale.tour_utils';

tour.register('shop_buy_rental_product_comparison', {
    test: true,
    url: '/shop?search=Computer',
},
    [
        {
            content: "click on add to comparison",
            trigger: '.o_add_compare',
        },
        {
            content: "Search Warranty write text",
            trigger: 'form input[name="search"]',
            run: "text Warranty",
        },
        {
            content: "Search Warranty click",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
        },
        {
            content: "add first product 'Warranty' in a comparison list",
            trigger: '.oe_product_cart:contains("Warranty") .o_add_compare',
        },
        {
            content: "check popover is now open and compare button contains two products",
            extra_trigger: '.comparator-popover',
            trigger: '.o_product_circle:contains(2)',
            run: function () {},
        },
        {
            content: "click on compare button",
            trigger: '.o_comparelist_button a',
        },
        {
            content: "Open daterangepicker",
            extra_trigger: '.o_product_comparison_table',
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
            content: "click on add to cart",
            trigger: '.product_summary:contains("Computer") .a-submit:contains("Add to Cart")',
        },
        tourUtils.goToCart({quantity: 1}),
        {
            content: "Verify there is a Computer",
            trigger: '#cart_products tbody td.td-product_name a strong:contains("Computer")',
            run: function () {}, // it's a check
        },
        {
            content: "Verify there are 1 quantity of Computers",
            trigger: '#cart_products tbody td.td-qty div.css_quantity input[value=1]',
            run: function () {}, // it's a check
        },
        {
            content: "go to checkout",
            extra_trigger: '#cart_products .oe_currency_value:contains(14.00)',
            trigger: 'a[href*="/shop/checkout"]',
        },
    ]
);
