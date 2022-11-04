/** @odoo-module */

import tour from 'web_tour.tour';
import { openCommandBar } from '../knowledge_tour_utils.js';


tour.register('knowledge_template_command_tour', {
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
}, { // click on the /template command
    trigger: '.oe-powerbox-commandName:contains("Template")',
    run: 'click',
}, { // wait for the block to appear in the editor
    trigger: '.o_knowledge_behavior_type_template',
}, { // enter text into the mail template
    trigger: '.o_knowledge_content > p',
    run: 'text Hello world'
}]);
