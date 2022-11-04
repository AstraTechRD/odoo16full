/** @odoo-module */

import tour from 'web_tour.tour';


tour.register('helpdesk_insert_kanban_view_link_in_knowledge', {
    url: '/web#action=helpdesk.helpdesk_ticket_action_main_tree',
    test: true,
}, [{ // switch to the kanban view
    trigger: 'button.o_switch_view.oi-view-kanban',
    run: 'click',
}, { // wait for the kanban view to load
    trigger: '.o_kanban_renderer',
}, { // open the filter menu
    trigger: '.o_filter_menu .dropdown-toggle',
}, { // pick a filter
    trigger: '.o_filter_menu .dropdown-item:contains("My Tickets")',
}, { // check that the facet is now active
    trigger: '.o_searchview .o_facet_value:contains("My Tickets")',
    run: () => {},
}, { // open the "favorite" menu
    trigger: '.o_favorite_menu .dropdown-toggle',
}, { // insert a view link in an article
    trigger: '.o_favorite_menu .dropdown-item:contains("Insert link in article")',
}, { // create a new article
    trigger: '.modal-footer button:contains("Create")',
    run: 'click',
}, { // wait for Knowledge to open
    trigger: '.o_knowledge_form_view',
}, { // the user should be redirected to the new article
    trigger: '.o_knowledge_behavior_type_view_link',
    run: 'dblclick',
}, { // check that the user is redirected to the view
    trigger: '.o_kanban_renderer',
}, { // check that the view has the selected facet
    trigger: '.o_searchview .o_facet_value:contains("My Tickets")',
}, { // check the title of the view
    trigger: '.o_control_panel .breadcrumb-item.active:contains("Tickets")',
}]);
