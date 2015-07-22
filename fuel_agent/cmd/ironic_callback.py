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

import json
import sys

import requests

from fuel_agent.utils import utils


def _process_error(message):
    sys.stderr.write(message)
    sys.stderr.write('\n')
    sys.exit(1)


def main():
    kernel_params = utils.parse_kernel_cmdline()
    api_url = kernel_params.get('api-url')
    deployment_id = kernel_params.get('deployment_id')
    if api_url is None or deployment_id is None:
        _process_error('Mandatory parameter ("api-url" or "deployment_id") is '
                       'missing.')

    bootif = kernel_params.get('BOOTIF')
    if bootif is None:
        _process_error('Cannot define boot interface, "BOOTIF" parameter is '
                       'missing.')

    boot_mac = bootif[3:].replace('-', ':')
    boot_ip = utils.get_interface_ip(boot_mac)
    if boot_ip is None:
        _process_error('Cannot find IP address of boot interface.')

    data = {"address": boot_ip,
            "status": "ready",
            "error_message": "no errors"}

    passthru = '%(api-url)s/v1/nodes/%(deployment_id)s/vendor_passthru' \
               '/pass_deploy_info' % {'api-url': api_url,
                                      'deployment_id': deployment_id}
    try:
        resp = requests.post(passthru, data=json.dumps(data),
                             headers={'Content-Type': 'application/json',
                                      'Accept': 'application/json'})
    except Exception as e:
        _process_error(str(e))

    if resp.status_code != 202:
        _process_error('Wrong status code %d returned from Ironic API' %
                       resp.status_code)
