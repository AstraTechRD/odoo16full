/** @odoo-module */

import tour from 'web_tour.tour';


tour.register('helpdesk_insert_graph_view_in_knowledge', {
    url: '/web#action=helpdesk.helpdesk_ticket_analysis_action',
    test: true,
}, [{ // open the filter menu
    trigger: '.o_filter_menu .dropdown-toggle',
}, { // pick a filter
    trigger: '.o_filter_menu .dropdown-item:contains("Urgent")',
}, { // check that the facet is now active
    trigger: '.o_searchview .o_facet_value:contains("Urgent")',
}, { // open the "group by" menu
    trigger: '.o_group_by_menu .dropdown-toggle',
}, { // pick a filter
    trigger: '.o_group_by_menu .dropdown-item:contains("Team")',
}, { // check that the facet is now active
    trigger: '.o_searchview .o_facet_value:contains("Team")',
}, { // open the "favorite" menu
    trigger: '.o_favorite_menu .dropdown-toggle',
}, { // insert the view in an article
    trigger: '.o_favorite_menu .dropdown-item:contains("Insert view in article")',
}, { // create a new article
    trigger: '.modal-footer button:contains("Create")',
}, { // wait for Knowledge to open
    trigger: '.o_knowledge_form_view',
}, { // the user should be redirected to the new article
    trigger: '.o_knowledge_behavior_type_embedded_view',
    run: function () {
        this.$anchor[0].scrollIntoView();
    },
}, { // check that the embedded view has the selected facet
    trigger: '.o_knowledge_behavior_type_embedded_view .o_searchview .o_facet_value:contains("Urgent")',
}, {
    trigger: '.o_knowledge_behavior_type_embedded_view .o_searchview .o_facet_value:contains("Team")',
}]);
