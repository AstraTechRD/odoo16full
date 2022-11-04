/** @odoo-module */

import tour from 'web_tour.tour';
import { openCommandBar } from '../knowledge_tour_utils.js';


tour.register('knowledge_file_command_tour', {
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
}, { // click on the /file command
    trigger: '.oe-powerbox-commandName:contains("File")',
    run: 'click',
}, { // wait for the media dialog to open
    trigger: '.o_select_media_dialog',
}, { // click on the first item of the modal
    trigger: '.o_existing_attachment_cell:first-child',
    run: 'click'
}, { // wait for the block to appear in the editor
    trigger: '.o_knowledge_behavior_type_file',
}]);
