/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('translate_sign_instructions', {
    test: true,
}, [
    {
        content: 'Translations must be loaded',
        trigger: 'iframe .o_sign_sign_item_navigator:contains("Cliquez pour commencer")',
        run: () => null, // it's a check
    }
]);
