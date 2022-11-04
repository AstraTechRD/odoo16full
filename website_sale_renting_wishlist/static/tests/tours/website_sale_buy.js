/** @odoo-module **/

import tour from 'web_tour.tour';
import tourUtils from 'website_sale.tour_utils';

tour.register('shop_buy_rental_product_wishlist', {
    test: true,
    url: '/shop?search=Computer',
},
    [
        {
            content: "click on add to wishlist",
            trigger: '.o_add_wishlist',
        },
        {
            content: "go to wishlist",
            extra_trigger: 'a[href="/shop/wishlist"] .badge.text-bg-primary:contains(1)',
            trigger: 'a[href="/shop/wishlist"]',
        },
        {
            content: "Open daterangepicker",
            extra_trigger: '.o_wish_rm',
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
            trigger: '.o_wish_add',
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
