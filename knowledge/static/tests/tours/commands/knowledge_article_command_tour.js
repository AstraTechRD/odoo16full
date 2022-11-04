/** @odoo-module */

import tour from 'web_tour.tour';
import { openCommandBar } from '../knowledge_tour_utils.js';


tour.register('knowledge_article_command_tour', {
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
}, { // click on the /article command
    trigger: '.oe-powerbox-commandName:contains("Article")',
    run: 'click',
}, { // set the value of the select2 input field
    trigger: '.o_knowledge_select2',
    run: function () {
        const $select = $(this.$anchor[0]);
        $select.select2('data', {
            id: 1,
            display_name: '📄 My Article'
        });
    },
}, { // click on the "Insert Link" button
    trigger: '.modal-footer button.btn-primary',
    run: 'click'
}, { // wait for the block to appear in the editor
    trigger: '.o_knowledge_behavior_type_article > span:contains("📄 My Article")'
}]);
