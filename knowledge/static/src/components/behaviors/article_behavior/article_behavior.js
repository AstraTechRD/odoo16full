/** @odoo-module */

import { _t } from "web.core";
import { AbstractBehavior } from "@knowledge/components/behaviors/abstract_behavior/abstract_behavior";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";

const { useEffect } = owl;


export class ArticleBehavior extends AbstractBehavior {
    setup () {
        super.setup();
        this.actionService = useService('action');
        this.dialogService = useService('dialog');
        useEffect(() => {
            /**
             * @param {Event} event
             */
            const onLinkClick = event => {
                event.preventDefault();
                event.stopPropagation();
                this.openArticle();
            };
            this.props.anchor.addEventListener('click', onLinkClick);
            return () => {
                this.props.anchor.removeEventListener('click', onLinkClick);
            };
        });
    }

    async openArticle () {
        try {
            await this.actionService.doAction('knowledge.ir_actions_server_knowledge_home_page', {
                additionalContext: {
                    res_id: parseInt(this.props.article_id)
                }
            });
        } catch (_) {
            this.dialogService.add(AlertDialog, {
                title: _t('Error'),
                body: _t("This article was deleted or you don't have the rights to access it."),
                confirmLabel: _t('Ok'),
            });
        }
    }
}

ArticleBehavior.template = "knowledge.ArticleBehavior";
ArticleBehavior.components = {};
ArticleBehavior.props = {
    ...AbstractBehavior.props,
    display_name: { type: String, optional: false },
    article_id: { type: Number, optional: false }
};
