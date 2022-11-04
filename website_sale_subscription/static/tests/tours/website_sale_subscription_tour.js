/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('shop_buy_subscription_product', {
    test: true,
    url: '/shop',
},
    [
        {
            content: "Search streaming write text",
            trigger: 'form input[name="search"]',
            run: "text Streaming SUB Week",
        },
        {
            content: "Search streaming click",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
        },
        {
            content: "Select streaming",
            trigger: '.oe_product_cart:first a:contains("Streaming SUB Weekly")',
        },
        {
            content: "Add one quantity",
            trigger: '.css_quantity a.js_add_cart_json i.fa-plus',
        },
        {
            content: "click on add to cart",
            trigger: '#product_detail form[action^="/shop/cart/update"] #add_to_cart',
        },
        {
            content: "See added t o cart + try to add other recurrence",
            trigger: '.my_cart_quantity:contains("2")',
            run: function () {
                window.location.href = '/@/shop';
            },
        },
        {
            content: "Search streaming monthly write text",
            trigger: 'form input[name="search"]',
            run: "text Streaming SUB month",
        },
        {
            content: "Search streaming monthly click",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
        },
        {
            content: "Select streaming monthly",
            trigger: '.oe_product_cart:first a:contains("Streaming SUB Monthly")',
        },
        {
            content: "Check that we cannot add streaming monthly",
            trigger: '#product_detail p:contains("This product has no valid combination.")',
            run: function () {}, // it's a check
        },
        {
            content: "go to cart",
            trigger: '.my_cart_quantity:contains("2")',
            run: function () {
                window.location.href = '/@/shop/cart';
            },
        },
    ]
);
