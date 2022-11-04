/** @odoo-module **/

import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { registry } from "@web/core/registry";

import { ImagesCarouselDialog } from './images_carousel_dialog';
import { SocialPostFormatterMixin } from "./social_post_formatter_mixin";

const { markup } = owl;

export class PostKanbanRecord extends KanbanRecord {
    formatPost (message) {
        return markup(SocialPostFormatterMixin._formatPost(message));
    }

    /**
     * Shows a bootstrap carousel starting at the clicked image's index
     *
     * @param {integer} index - index of the default image to be displayed
     * @param {array} images - array of all the images to display
     */
     onClickMoreImages(index, images) {
        this.dialog.add(ImagesCarouselDialog, {
            title: this.env._t("Post Images"),
            activeIndex: index,
            images: images
        })
    }
}

export class PostKanbanRenderer extends KanbanRenderer {}

PostKanbanRenderer.components = {
    ...KanbanRenderer.components,
    KanbanRecord: PostKanbanRecord,
};


export const PostKanbanView = {
    ...kanbanView,
    Renderer: PostKanbanRenderer,
};

registry.category("views").add("social_post_kanban_view", PostKanbanView);
