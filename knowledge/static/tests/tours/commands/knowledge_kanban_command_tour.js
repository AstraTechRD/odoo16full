/** @odoo-module */

import tour from 'web_tour.tour';
import { openCommandBar } from '../knowledge_tour_utils.js';


tour.register('knowledge_kanban_command_tour', {
    url: '/web',
    test: true,
}, [tour.stepUtils.showAppsMenuItem(), {
    // open the Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
}, { // open the command bar
    trigger: '.odoo-editor-editable > p',
    run: function () {
        openCommandBar(this.$anchor[0]);
    },
}, { // click on the /kanban command
    trigger: '.oe-powerbox-commandName:contains("Kanban view")',
    run: 'click',
}, { // choose a name for the embedded view
    trigger: '.modal-footer button.btn-primary'
}, { // scroll to the embedded view to load it
    trigger: '.o_knowledge_behavior_type_embedded_view',
    run: function () {
        this.$anchor[0].scrollIntoView();
    },
}, { // wait for the kanban view to be mounted
    trigger: '.o_knowledge_behavior_type_embedded_view .o_kanban_renderer'
}, { // create an article item
    trigger: '.o_knowledge_behavior_type_embedded_view .o-kanban-button-new',
    run: 'click',
}]);
