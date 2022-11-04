/** @odoo-module */

import tour from 'web_tour.tour';

tour.register('access_helpdesk_article_portal_tour', {
    test: true,
}, [{
    content: "clik on 'Help'",
    trigger: 'a[role="menuitem"]:contains("Help")',
}, {
    content: "Write 'Article' in the search bar",
    trigger: 'input[name="search"]',
    run: 'text Article'
}, {
    content: "Check that results contain 'Helpdesk Article'",
    trigger: '.dropdown-item:contains("Helpdesk Article")',
    run() {},
}, {
    content: "Check that results contain 'Child Article'",
    trigger: '.dropdown-item:contains("Child Article")',
    run() {},
}, {
    content: "Check that results don't contain 'Other Article'",
    trigger: '.dropdown-menu:not(:has(.dropdown-item:contains("Other Article")))',
    run() {},
}, {
    content: "Click on 'Browse Articles'",
    trigger: 'a:contains("Browse Articles")',
}, {
    content: "Check that the 'Helpdesk Article' is selected",
    trigger: '.o_article_active:contains("Helpdesk Article")',
    run() {},
}, {
    content: "Check that the 'Helpdesk Article' is unfolded",
    trigger: '.o_article_name:contains("Child Article")',
    run() {},
}]);
