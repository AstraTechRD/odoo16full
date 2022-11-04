/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * This service store data from non-knowledge form view records that can be used
 * by a Knowledge form view.
 *
 * A typical usage could be the following:
 * - A form view is loaded and one field of the current record is a match for
 *   Knowledge @see FormControllerPatch
 *   - Information about this record and how to access its form view is stored
 *     in this @see KnowledgeCommandsService .
 * - A knowledge Article is opened and it contains a @see TemplateBehavior .
 *   - When the behavior is injected (@see HtmlFieldPatch ) in the view, it
 *     asks this @see KnowledgeCommandsService if the record can be interacted
 *     with.
 *   - if there is one such record, the related buttons are displayed in the
 *     toolbar of the behavior.
 * - When one such button is used, the form view of the record is reloaded
 *   and the button action is executed through a @see Macro .
 *   - an exemple of macro action would be copying the template contents as the
 *     value of a field_html of the record, such as "description"
 *
 * Scope of the service:
 * It is meant to be called on 2 occasions:
 * 1) by @see FormControllerPatch :
 *        It will only be called if the viewed record can be used within the
 *        Knowledge module. Such a record should have a chatter in its form
 *        view, or have at least one field in a whitelist specified in the
 *        controller that is visible and editable by the current user.
 * 2) by @see TemplateBehavior or @see FileBehavior :
 *        It will be called by a behavior to check whether it has a record that
 *        can be interacted with in the context of the toolbar (withChatter or
 *        withHtmlField).
 */
export const knowledgeCommandsService = {
    start(env) {
        let commandsRecordInfo = null;

        /**
         * @param {Object} recordInfo
         * @param {number} [recordInfo.resId] id of the target record
         * @param {string} [recordInfo.resModel] model name of the target record
         * @param {Array} [recordInfo.breadcrumbs] array of breadcrumbs objects
         *                {jsId, name} leading to the target record
         * @param {boolean} [recordInfo.withChatter] target record has a chatter
         * @param {boolean} [recordInfo.withHtmlField] target record has a
         *                   targeted html field @see FormControllerPatch
         * @param {Object} [recordInfo.fieldInfo] info object for the html field
         *                 {string, name}
         * @param {XMLDocument} [recordInfo.fieldInfo] xml document (arch of the
         *                      view of the target record)
         */
        function setCommandsRecordInfo(recordInfo) {
            commandsRecordInfo = recordInfo;
        }

        function getCommandsRecordInfo() {
            return commandsRecordInfo;
        }

        const knowledgeCommandsService = {
            setCommandsRecordInfo,
            getCommandsRecordInfo,
        };
        return knowledgeCommandsService;
    }
};

registry.category("services").add("knowledgeCommandsService", knowledgeCommandsService);
