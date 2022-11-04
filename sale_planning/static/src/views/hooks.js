/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { serializeDateTime } from "@web/core/l10n/dates";

const { useComponent, useEnv } = owl;

export function useSalePlanningViewHook({ getDomain, getViewContext, getScale, getFocusDate }) {
    const component = useComponent();
    const env = useEnv();
    const actionService = useService("action");
    const orm = useService("orm");
    const notification = useService("notification");
    return {
        onClickPlanOrders: async () => {
            const result = await orm.call(
                component.model.resModel,
                "action_plan_sale_order",
                [getDomain()],
                {
                    context: getViewContext(),
                },
            );
            if (!result.length) {
                notification.add(
                    env._t("There are no sales orders to assign or no employees are available."),
                    {
                        type: "danger",
                    },
                );
            } else {
                const scale = getScale();
                const viewType = env.config.viewType;
                notification.add(
                    env._t("The sales orders have successfully been assigned."),
                    {
                        type: "success",
                        buttons: [{
                            name: env._t("View Shifts"),
                            icon: "fa-arrow-right",
                            onClick: () => {
                                actionService.doAction("sale_planning.planning_action_orders_planned", {
                                    viewType,
                                    additionalContext: {
                                        active_ids: result,
                                        default_scale: scale,
                                        default_mode: scale,
                                        initial_date: serializeDateTime(getFocusDate()),
                                    },
                                });
                            },
                        }],
                    },
                );
            }
            component.model.load();
        },
    }
}
