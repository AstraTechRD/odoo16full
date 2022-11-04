/** @odoo-module **/

import publicWidget from 'web.public.widget';


publicWidget.registry.RentalSearchSnippet = publicWidget.Widget.extend({
    selector: '.s_rental_search',
    events: {
        'click .s_rental_search_btn': '_onClickRentalSearchButton',
        'toggle_search_btn .o_website_sale_daterange_picker': 'onToggleSearchBtn',
    },

    onToggleSearchBtn(ev) {
        ev.currentTarget.querySelector('.s_rental_search_btn').disabled = Boolean(ev.detail);
    },

    /**
     * This function is triggered when the user clicks on the rental search button.
     * @param ev
     */
    _onClickRentalSearchButton(ev) {
        const rentalSearch = ev.currentTarget.closest('.s_rental_search');
        const searchParams = new URLSearchParams();
        const rawInput = document.querySelector('.daterange-input').value;
        const [startDate, endDate] = rawInput.split(' - ');
        if (startDate && endDate) {
            searchParams.append('start_date', `${new Date(startDate).toISOString()}`);
            searchParams.append('end_date', `${new Date(endDate).toISOString()}`);
        }
        const productAttributeId = rentalSearch.querySelector('.product_attribute_search_rental_name').id;

        const productAttributeValueId = rentalSearch.querySelector('.s_rental_search_select').value;
        if (productAttributeValueId) {
            searchParams.append('attrib', `${productAttributeId}-${productAttributeValueId}`);
        }
        window.location = `/shop?${searchParams.toString()}`;
    },
});


export default publicWidget.registry.RentalSearchSnippet;
