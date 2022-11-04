/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { ActionSwiper } from "@web/core/action_swiper/action_swiper";

const { Component } = owl;

export class SwiperView extends Component {
    setup() {
        useUpdate({
            func: () => {
                // to observe useful values outside of slot, to guarantee proper re-render
                if (this.swiperView) {
                    this.swiperView.record.localId;
                    this.swiperView.componentName;
                }
            },
        });
    }
    /**
     * @returns {SwiperView}
     */
    get swiperView() {
        return this.props.record;
    }
}

Object.assign(SwiperView, {
    components: { ActionSwiper },
    props: { record: Object },
    template: 'mail_enterprise.SwiperView',
});

registerMessagingComponent(SwiperView);
