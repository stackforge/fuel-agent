#!/bin/bash

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

ROOT=$(dirname `readlink -f $0`)

function run_unit {
  local result=0
  pushd $ROOT >> /dev/null
  tox -epy26 || result=1
  popd >> /dev/null
  return $result
}

function run_pep8 {
  local result=0
  pushd $ROOT >> /dev/null
  tox -epep8 || result=1
  popd >> /dev/null
  return $result
}


result=0
run_pep8 || result=1
run_unit || result=1

exit $result