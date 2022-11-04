/** @odoo-module **/

import field_registry from "web.field_registry";
import "@mail/js/activity";

const KanbanActivity = field_registry.get("kanban_activity");
const ListActivity = field_registry.get("list_activity");

function applyInclude(Activity) {
  Activity.include({
    events: Object.assign({}, Activity.prototype.events, {
      "click .o_mark_as_done_request_sign": "_onClickRequestSign",
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRequestSign(ev) {
      ev.preventDefault();
      this.do_action("sign.action_sign_send_request", {
        additional_context: {
          sign_directly_without_mail: false,
          default_activity_id: $(ev.currentTarget).data("activity-id"),
        },
        on_close: this._reload.bind(this),
      });
    },
  });
}

applyInclude(KanbanActivity);
applyInclude(ListActivity);
