/** @odoo-module */

import { Domain } from "@web/core/domain";
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

const { useEffect } = owl;

/**
 * Knowledge articles can interact with some records with the help of the
 * @see KnowledgeCommandsService .
 * Those records need to have specific html field which name is in the following
 * list. This list is ordered and the first match found in a record will take
 * precedence. Once a match is found, it is stored in the
 * KnowledgeCommandsService to be accessed later by an article.
 */
const KNOWLEDGE_RECORDED_FIELD_NAMES = [
    'note',
    'memo',
    'description',
    'comment',
    'narration',
    'additional_note',
    'internal_notes',
    'notes',
];

const FormControllerPatch = {
    setup() {
        this._super(...arguments);
        this.knowledgeCommandsService = useService('knowledgeCommandsService');
        // useEffect based on the id of the current record, in order to
        // properly register a newly created record, or the switch to another
        // record without leaving the current form view.
        useEffect(
            () => this._commandsRecordInfoRegistration(),
            () => [this.model.root.data.id],
        );
    },
    /**
     * Copy of the breadcrumbs array used as an identifier for a
     * commandsRecordInfo object.
     *
     * @returns {Array[Object]}
     */
    _getBreadcrumbsIdentifier() {
        return this.env.config.breadcrumbs.map(breadcrumb => {
            return {
                jsId: breadcrumb.jsId,
                name: breadcrumb.name,
            };
        });
    },
    /**
     * Update the @see KnowledgeCommandsService to clean obsolete
     * commandsRecordInfo and to register a new one if the current record
     * can be used by certain Knowledge commands.
     */
    _commandsRecordInfoRegistration() {
        if (this.env.config.breadcrumbs && this.env.config.breadcrumbs.length) {
            if (this.props.resModel === 'knowledge.article') {
                this._unregisterCommandsRecordInfo(this._getBreadcrumbsIdentifier());
            } else if (this.model.root.data.id) {
                this._searchCommandsRecordInfo();
            }
        }
    },
    /**
     * Evaluate a given modifier (i.e. invisible) from the raw code of the view
     * based on the raw value and the context of the given record.
     *
     * @param {Object} record raw record
     * @param {string} modifier modifier as registered in the view (xml)
     * @returns {boolean}
     */
    _evalModifier(record, modifier) {
        if (!modifier) {
            return false;
        }
        try {
            const preDomain = new Domain(modifier); // unaware of context
            const domain = new Domain(preDomain.toList(record.context)); // aware of context
            return domain.contains(record.data);
        } catch {
            return true;
        }
    },
    /**
     * Evaluate the current record and notify @see KnowledgeCommandsService if
     * it can be used in a Knowledge article.
     */
    _searchCommandsRecordInfo() {
        /**
         * this.model.__bm__.get([...] {raw: true}) is used to get the raw data
         * of the record (and not the post-processed this.model.root.data).
         * This is because invisible and readonly modifiers from the raw code of
         * the view have to be evaluated to check whether the current user has
         * access to a specific element in the view (i.e.: chatter or
         * html_field), and @see Domain is currently only able to evaluate such
         * a domain with the raw data.
         */
        const record = this.model.__bm__.get(this.model.root.__bm_handle__, {raw: true});
        const formFields = this.props.archInfo.activeFields;
        const fields = this.props.fields;
        const xmlDoc = this.props.archInfo.xmlDoc;
        const breadcrumbs = this._getBreadcrumbsIdentifier();
        // format stored by the knowledgeCommandsService
        const commandsRecordInfo = {
            resId: this.model.root.data.id,
            resModel: this.props.resModel,
            breadcrumbs: breadcrumbs,
            withChatter: false,
            withHtmlField: false,
            fieldInfo: {},
            xmlDoc: this.props.archInfo.xmlDoc,
        };

        /**
         * If the current potential record has exactly the same breadcrumbs
         * sequence as another record registered in the
         * @see KnowledgeCommandsService , the previous record should be
         * unregistered here because this problem will not be caught later, as
         * the Knowledge form view only checks whether its breadcrumbs sequence
         * contains a record's breadcrumbs sequence, regardless of the fact that
         * the current potential record may not have been registered in the
         * service.
         *
         * This call could be omitted if the breadcrumbs would also store the
         * related res_id if any, but currently two records with the same
         * display name and model will have exactly the same breadcrumbs
         * information (controllerID and title).
         */
        this._unregisterCommandsRecordInfo(breadcrumbs, true);

        // check whether the form view has a chatter with messages
        const chatterNode = this.props.archInfo.xmlDoc.querySelector('.oe_chatter');
        if (chatterNode && chatterNode.querySelector('field[name="message_ids"]')) {
            commandsRecordInfo.withChatter = true;
            this.knowledgeCommandsService.setCommandsRecordInfo(commandsRecordInfo);
        }

        // check if there is any html field usable with knowledge
        loopFieldNames: for (const fieldName of KNOWLEDGE_RECORDED_FIELD_NAMES) {
            if (fieldName in formFields &&
                fields[fieldName].type === 'html' &&
                !fields[fieldName].readonly
            ) {
                const readonlyModifier = formFields[fieldName].modifiers.readonly;
                const invisibleModifier = formFields[fieldName].modifiers.invisible;
                if (this._evalModifier(record, readonlyModifier) || this._evalModifier(record, invisibleModifier)) {
                    continue loopFieldNames;
                }
                // Parse the xmlDoc recursively through parents to evaluate
                // eventual invisible modifiers.
                const xmlFieldParent = xmlDoc.querySelector(`field[name="${fieldName}"]`).parentElement;
                let xmlInvisibleParent = xmlFieldParent.closest('[modifiers*="invisible"]');
                while (xmlInvisibleParent) {
                    const invisibleParentModifier = JSON.parse(xmlInvisibleParent.getAttribute('modifiers')).invisible;
                    if (this._evalModifier(record, invisibleParentModifier)) {
                        continue loopFieldNames;
                    }
                    xmlInvisibleParent = xmlInvisibleParent.parentElement &&
                        xmlInvisibleParent.parentElement.closest('[modifiers*="invisible"]');
                }
                commandsRecordInfo.fieldInfo = {
                    name: fieldName,
                    string: fields[fieldName].string,
                };
                break;
            }
        }
        if (commandsRecordInfo.fieldInfo.name) {
            commandsRecordInfo.withHtmlField = true;
            this.knowledgeCommandsService.setCommandsRecordInfo(commandsRecordInfo);
        }
    },
    /**
     * Compare the current breadcrumbs identifier with a previously registered
     * commandsRecordInfo and unregister it if they don't match.
     *
     * @param {Array[Object]} breadcrumbs
     * @param {boolean} revoke whether to unregister the commandsRecordInfo when
     *                  breadcrumbs match (revoke = true) or when they don't
     *                  match (revoke = false)
     */
    _unregisterCommandsRecordInfo(breadcrumbs, revoke = false) {
        function areBreadcrumbsArraysEqual(firstBreadcrumbsArray, secondBreadcrumbsArray) {
            for (let i = 0; i < firstBreadcrumbsArray.length; i++) {
                if (firstBreadcrumbsArray[i].jsId !== secondBreadcrumbsArray[i].jsId ||
                    firstBreadcrumbsArray[i].name !== secondBreadcrumbsArray[i].name) {
                    return false;
                }
            }
            return true;
        }
        const commandsRecordInfo = this.knowledgeCommandsService.getCommandsRecordInfo();
        if (!commandsRecordInfo) {
            return;
        }
        let shouldUnregister = revoke;
        if (commandsRecordInfo.breadcrumbs.length > breadcrumbs.length) {
            shouldUnregister = !revoke;
        } else {
            const slicedBreadcrumbs = breadcrumbs.slice(0, commandsRecordInfo.breadcrumbs.length);
            if (areBreadcrumbsArraysEqual(commandsRecordInfo.breadcrumbs, slicedBreadcrumbs)) {
                shouldUnregister = revoke;
            } else {
                shouldUnregister = !revoke;
            }
        }
        if (shouldUnregister) {
            this.knowledgeCommandsService.setCommandsRecordInfo(null);
        }
    },
};

patch(FormController.prototype, 'register_knowledge_fields', FormControllerPatch);
