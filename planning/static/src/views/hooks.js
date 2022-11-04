/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";
import { serializeDateTime } from "@web/core/l10n/dates";

const { markup, useComponent, useEnv } = owl;

export function usePlanningViewHook({ getDomain, getStartDate, getRecords, getAdditionalContext }) {
    const component = useComponent();
    const env = useEnv();
    const actionService = useService("action");
    const notifications = useService("notification");
    const orm = useService("orm");
    return {
        onClickCopyPrevious: async () => {
            const startDate = serializeDateTime(getStartDate());
            const result = await orm.call(
                component.model.resModel,
                "action_copy_previous_week",
                [startDate, getDomain()],
            );
            if (result) {
                const message = env._t("The shifts from the previous week have successfully been copied.");
                notifications.add(
                    markup(`<i class="fa fa-fw fa-check"></i><span class="ms-1">${escape(message)}</span>`),
                    {
                        type: "success",
                    },
                );
            } else {
                notifications.add(
                    env._t("There are no shifts planned for the previous week, or they have already been copied."),
                    {
                        type: "danger",
                    },
                );
            }
            await component.model.load();
        },

        onClickPublish: async () => {
            const records = getRecords();
            if (!records || records.length === 0) {
                return notifications.add(
                    env._t("The shifts have already been published, or there are no shifts to publish."),
                    {
                        type: "danger",
                    },
                );
            }
            return actionService.doAction("planning.planning_send_action", {
                additionalContext: getAdditionalContext(),
                onClose: component.model.load.bind(component.model),
            });
        },
    }
}
