/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'SwiperView',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * Handles left swipe on this swiper view.
         */
        onLeftSwipe() {
            if (this.channelPreviewViewOwner) {
                this.channelPreviewViewOwner.thread.unpin();
            }
        },
        /**
         * Handles right swipe on this swiper view.
         */
        onRightSwipe() {
            if (this.channelPreviewViewOwner) {
                if (this.channelPreviewViewOwner.thread.lastNonTransientMessage) {
                    this.channelPreviewViewOwner.thread.markAsSeen(this.channelPreviewViewOwner.thread.lastNonTransientMessage);
                }
            }
            if (this.messageViewOwner) {
                this.messageViewOwner.message.markAsRead();
            }
            if (this.notificationGroupViewOwner) {
                if (this.notificationGroupViewOwner.notificationGroup.notifications.length > 0) {
                    this.notificationGroupViewOwner.notificationGroup.notifyCancel();
                }
            }
            if (this.threadNeedactionPreviewViewOwner) {
                this.models['Message'].markAllAsRead([
                    ['model', '=', this.threadNeedactionPreviewViewOwner.thread.model],
                    ['res_id', '=', this.threadNeedactionPreviewViewOwner.thread.id],
                ]);
            }
        },
    },
    fields: {
        channelPreviewViewOwner: one('ChannelPreviewView', {
            identifying: true,
            inverse: 'swiperView',
        }),
        componentName: attr({
            compute() {
                if (this.channelPreviewViewOwner) {
                    return 'ChannelPreviewView';
                }
                if (this.messageViewOwner) {
                    return 'Message';
                }
                if (this.notificationGroupViewOwner) {
                    return 'NotificationGroup';
                }
                if (this.threadNeedactionPreviewViewOwner) {
                    return 'ThreadNeedactionPreview';
                }
                return clear();
            },
            required: true,
        }),
        hasLeftSwipe: attr({
            compute() {
                if (this.channelPreviewViewOwner) {
                    return (
                        this.channelPreviewViewOwner.thread.isChatChannel &&
                        this.channelPreviewViewOwner.thread.isPinned
                    );
                }
                return false;
            },
            required: true,
        }),
        hasRightSwipe: attr({
            compute() {
                if (this.channelPreviewViewOwner) {
                    return this.channelPreviewViewOwner.channel.localMessageUnreadCounter > 0;
                }
                if (this.messageViewOwner) {
                    return true;
                }
                if (this.notificationGroupViewOwner) {
                    return true;
                }
                if (this.threadNeedactionPreviewViewOwner) {
                    return true;
                }
                return false;
            },
            required: true,
        }),
        leftSwipeBackgroundColor: attr({
            compute() {
                if (this.channelPreviewViewOwner) {
                    return 'bg-danger';
                }
                return clear();
            },
        }),
        leftSwipeIcon: attr({
            compute() {
                if (this.channelPreviewViewOwner) {
                    return 'fa-times-circle';
                }
                return clear();
            },
        }),
        messageViewOwner: one('MessageView', {
            identifying: true,
            inverse: 'swiperView',
        }),
        notificationGroupViewOwner: one('NotificationGroupView', {
            identifying: true,
            inverse: 'swiperView',
        }),
        record: one('Record', {
            compute() {
                if (this.channelPreviewViewOwner) {
                    return this.channelPreviewViewOwner;
                }
                if (this.messageViewOwner) {
                    return this.messageViewOwner;
                }
                if (this.notificationGroupViewOwner) {
                    return this.notificationGroupViewOwner;
                }
                if (this.threadNeedactionPreviewViewOwner) {
                    return this.threadNeedactionPreviewViewOwner;
                }
                return clear();
            },
            required: true,
        }),
        rightSwipeBackgroundColor: attr({
            compute() {
                if (this.channelPreviewViewOwner) {
                    return 'bg-success';
                }
                if (this.messageViewOwner) {
                    return 'bg-success';
                }
                if (this.notificationGroupViewOwner) {
                    return 'bg-warning';
                }
                if (this.threadNeedactionPreviewViewOwner) {
                    return 'bg-success';
                }
                return clear();
            },
        }),
        rightSwipeIcon: attr({
            compute() {
                if (this.channelPreviewViewOwner) {
                    return 'fa-check-circle';
                }
                if (this.messageViewOwner) {
                    return 'fa-check-circle';
                }
                if (this.notificationGroupViewOwner) {
                    return 'fa-times-circle';
                }
                if (this.threadNeedactionPreviewViewOwner) {
                    return 'fa-check-circle';
                }
                return clear();
            },
        }),
        threadNeedactionPreviewViewOwner: one('ThreadNeedactionPreviewView', {
            identifying: true,
            inverse: 'swiperView',
        }),
    },
});
