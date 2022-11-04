/** @odoo-module */

import { FormController } from '@web/views/form/form_controller';

export class KnowledgeArticleFormController extends FormController {}

// Open articles in edit mode by default
KnowledgeArticleFormController.defaultProps = {
    ...FormController.defaultProps,
    mode: 'edit',
};
