# -*- coding: utf-8 -*-

#    Copyright 2015 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from fuel_bootstrap.objects import master_node_settings


def notify_webui_on_fail(function):
    def wrapper(*args, **kwargs):
        try:
            function(*args, **kwargs)
        except Exception:
            notify_webui("Last bootstrap image activation was failed."
                         " It's possible that nodes will not discovered"
                         " after reboot.")
            raise
    return wrapper


def notify_webui_on_first_run(function):
    def wrapper(*args, **kwargs):
        from fuel_bootstrap.utils import bootstrap_image as bs_image
        if bs_image.is_stub_active():
            notify_webui("There is no active bootstrap. Bootstrap image"
                         " building is in progress. Please reboot failed"
                         " to discover nodes after bootstrap image become"
                         " available.")
        function(*args, **kwargs)
    return wrapper


def notify_webui(error_message):
    mn_settings = master_node_settings.MasterNodeSettings()
    settings = mn_settings.get()
    settings['settings'].setdefault('bootstrap', {}).setdefault('error', {})
    settings['settings']['bootstrap']['error']['value'] = error_message
    mn_settings.update(settings)
