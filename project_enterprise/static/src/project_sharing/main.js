/** @odoo-module  **/

import { hasTouch } from "@web/core/browser/feature_detection";
import { prepareFavoriteMenuRegister } from '@project/project_sharing/components/favorite_menu_registry';
import { startWebClient } from '@web/start';
import { ProjectSharingWebClient } from '@project/project_sharing/project_sharing';
import { removeServices } from './remove_services';

prepareFavoriteMenuRegister();
removeServices();
(async () => {
    await startWebClient(ProjectSharingWebClient);
    document.body.classList.toggle("o_touch_device", hasTouch());
})();
