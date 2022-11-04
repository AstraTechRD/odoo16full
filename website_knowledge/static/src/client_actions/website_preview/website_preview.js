/** @odoo-module **/
import { patch } from 'web.utils';
import { WebsitePreview } from '@website/client_actions/website_preview/website_preview';

patch(WebsitePreview.prototype, 'website_knowledge_website_preview', {
    /**
     * @override
     */
    _isTopWindowURL({ pathname }) {
        return (
            pathname && (
                pathname.startsWith('/knowledge/article/')
                || pathname.includes('/knowledge/home')
            )
        ) || this._super(...arguments);
    }
});
