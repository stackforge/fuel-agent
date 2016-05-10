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

set -e

ROOT=$(dirname `readlink -f $0`)

function usage {
  echo "Usage: $0 [OPTION]..."
  echo "Run Fuel-Agent test suite(s)"
  echo ""
  echo "  -h, --help                  Print this usage message"
  echo "  -A, --no-agent              Skip Fuel Agent tests"
  echo "  -B, --no-bootstrap          Skip Fuel Bootstrap tests"
  echo ""
  echo "Note: with no options specified, the script will try to run all available"
  echo "      tests with all available checks."
  exit
}

function process_options {
  for arg in $@; do
    case "$arg" in
      -h|--help) usage;;
      -A|--no-agent) agent_tests=0;;
      -B|--no-bootstrap) bootstrap_tests=0
    esac
  done
}

agent_tests=1
bootstrap_tests=1

function run_cleanup {
  find . -type f -name "*.pyc" -delete
}

function run_tests {
    run_cleanup

    if [ $agent_tests -eq 1 ]; then
        run_agent_tests
    fi

    if [ $bootstrap_tests -eq 1 ]; then
        run_bootstrap_tests
    fi
}

function run_agent_tests {
    tox -v
}

function run_bootstrap_tests {
    pushd "$ROOT/contrib/fuel_bootstrap/fuel_bootstrap_cli" >> /dev/null
    tox -v
    popd >> /dev/null
}

process_options $@
run_tests
