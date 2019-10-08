#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2018, Doron Chosnek
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
author: Brandon Beck (@techbeck03)
description: Enables creation, modification, deletion and query of agent nat configs
extends_documentation_fragment: tetration
module: tetration_agent_nat_config
notes:
- Requires the tetpyclient Python module.
- Supports check mode.
options:
  nat_config_id:
    description:
    - Numeric ID of existing agent nat configuration
    - Require one of [C(vrf_name), C(vrf_id), C(nat_config_id)]
    - Mutually exclusive to C(vrf_name) and C(vrf_id)
    type: string
  src_port_range_end:
    description:
    - Upper bound of source port range (0-65535)
    - Required if I(state=present) or I(state=query)
    type: int
  src_port_range_start:
    description:
    - Lower bound of source port range (0-65535)
    - Required if I(state=present) or I(state=query)
    type: int
  src_subnet:
    description:
    - Subnet to which source IP can belong to (CIDR notation)
    - Requried if I(state=present) or I(state=query)
    type: string
  state:
    choices: '[present, absent, query]'
    default: present
    description: Add, change, remove or query for agent nat configs
    required: true
    type: string
  vrf_id:
    description:
    - VRF ID for tagging flows for agents
    - Require one of [C(vrf_name), C(vrf_id), C(nat_config_id)]
    - Mutually exclusive to C(vrf_name) and C(nat_config_id)
    type: int
  vrf_name:
    description:
    - VRF name for tagging flows for agents
    - Require one of [C(vrf_name), C(vrf_id), C(nat_config_id)]
    - Mutually exclusive to C(vrf_id) and C(nat_config_id)
    type: string
requirements: tetpyclient
version_added: '2.8'
'''

EXAMPLES = r'''
# Add or Modify an agent nat config
tetration_agent_nat_config:
    src_subnet: 172.16.109.51/32
    src_port_range_start: 0
    src_port_range_end: 65535
    vrf_name: Default
    state: present
    provider:
      host: "tetration-cluster@company.com"
      api_key: 1234567890QWERTY
      api_secret: 1234567890QWERTY

# Query for agent nat config
tetration_agent_nat_config:
    src_subnet: 172.16.109.51/32
    src_port_range_start: 0
    src_port_range_end: 65535
    vrf_name: Default
    state: query
    provider:
      host: "tetration-cluster@company.com"
      api_key: 1234567890QWERTY
      api_secret: 1234567890QWERTY

# Remove agent nat config
tetration_agent_nat_config:
    src_subnet: 172.16.109.51/32
    vrf_name: Default
    state: absent
    provider:
      host: "tetration-cluster@company.com"
      api_key: 1234567890QWERTY
      api_secret: 1234567890QWERTY
'''

RETURN = r'''
---
object:
  contains:
    created_at:
      description: Date of agent nat config creation (Unix Epoch)
      returned: when C(state) is present or query
      sample: 1553193603
      type: int
    id:
      description: Unique identifier for the agent nat config entry
      returned: when C(state) is present or query
      sample: 5c93da83497d4f33d7145960
      type: int
    src_port_range_end:
      description: Upper bound of source port range (0-65535)
      returned: when C(state) is present or query
      sample: 65535
      type: int
    src_port_range_start:
      description: Lower bound of source port range (0-65535)
      returned: when C(state) is present or query
      sample: 0
      type: int
    src_subnet:
      description: Subnet to which source IP can belong to (CIDR notation).
      returned: when C(state) is present or query
      sample: 172.16.109.51/32
      type: string
    updated_at:
      description: Date of agent nat config last modification (Unix Epoch)
      returned: when C(state) is present or query
      sample: 1556060982
      type: int
    vrf_id:
      description: VRF ID to use for tagging flows for agents whose source address
        and port falls in the above specified range.
      returned: when C(state) is present or query
      sample: 676734
      type: int
  description: the changed or modified object
  returned: always
  type: complex
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.tetration.api import TetrationApiModule
from ansible.module_utils.tetration.api import TETRATION_API_AGENT_NAT_CONFIG
from ansible.module_utils.tetration.api import TETRATION_API_TENANT

from ansible.utils.display import Display
display = Display()

def main():
    tetration_spec=dict(
        src_subnet=dict(type='str', required=False),
        src_port_range_start=dict(type='int', required=False),
        src_port_range_end=dict(type='int', required=False),
        vrf_name=dict(type='str', required=False),
        vrf_id=dict(type='int', required=False),
        nat_config_id=dict(type='str', required=False),
    )

    argument_spec = dict(
        provider=dict(required=True),
        state=dict(required=True, choices=['present', 'absent', 'query'])
    )

    argument_spec.update(tetration_spec)
    argument_spec.update(TetrationApiModule.provider_spec)

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ['state', 'present', ['src_subnet', 'src_port_range_start', 'src_port_range_end']],
            ['state', 'query', ['src_subnet', 'src_port_range_start', 'src_port_range_end']],
        ],
        required_one_of=[
            ['vrf_name', 'vrf_id', 'nat_config_id'],
        ],
        mutually_exclusive=[
            ['vrf_name', 'vrf_id', 'nat_config_id'],
        ]
    )

    tet_module = TetrationApiModule(module)
    # These are all elements we put in our return JSON object for clarity
    result = dict(
        changed=False,
        api_version=module.params['provider']['api_version'],
        tetration=module.params['provider']['server_endpoint'],
        object=None,
    )

    state = module.params['state']
    src_subnet = module.params['src_subnet']
    src_port_range_start = module.params['src_port_range_start']
    src_port_range_end = module.params['src_port_range_end']
    vrf_name = module.params['vrf_name']
    vrf_id = module.params['vrf_id']
    nat_config_id = module.params['nat_config_id']

    # Check if valid parameters are passed for absent state
    if state == 'absent' and not nat_config_id and not (vrf_id or vrf_name) and not (src_subnet and src_port_range_end and src_port_range_start):
        module.fail_json(msg='Either a valid nat config id or vrf, src_subnet, src_port_range_start, and src_port_range_end is required for state \'absent\'')

    # =========================================================================
    # Get current state of the object

    # Get existing nat config by nat config id if passed
    if nat_config_id:
        existing_object = tet_module.get_object(
            target = TETRATION_API_AGENT_NAT_CONFIG,
            filter = dict(id=nat_config_id),
            sub_element='results'
        )
        result['object'] = existing_object
    # Get existing nat config by vrf id if passed
    elif vrf_id:
        existing_object = tet_module.get_object(
            target = TETRATION_API_AGENT_NAT_CONFIG,
            filter = dict(
                vrf_id=vrf_id,
                src_subnet=src_subnet,
                src_port_range_start=src_port_range_start,
                src_port_range_end=src_port_range_end
            ),
            sub_element='results'
        )
        result['object'] = existing_object
    # Get existing nat config by name if passed
    else:
        existing_object = tet_module.get_object(
            target = TETRATION_API_TENANT,
            filter = dict(
                name=vrf_name
            )
        )
        if not existing_object:
            module.fail_json(msg='A vrf could not be found matching vrf name: %s' % vrf_name)
        else:
            vrf_id = existing_object['id']
        existing_object = tet_module.get_object(
            target = TETRATION_API_AGENT_NAT_CONFIG,
            filter = dict(
                vrf_id=vrf_id,
                src_subnet=src_subnet,
                src_port_range_start=src_port_range_start,
                src_port_range_end=src_port_range_end
            ),
            sub_element='results'
        )
        result['object'] = existing_object

    # =========================================================================
    # Now enforce the desired state (present, absent, query)

    # ---------------------------------
    # STATE == 'present'
    # ---------------------------------
    if state == 'present':
        # if the object does not exist at all, create it
        new_object = dict(
            src_subnet=src_subnet,
            src_port_range_start=src_port_range_start,
            src_port_range_end=src_port_range_end,
            vrf_id=vrf_id
        )
        if not bool(existing_object):
            result['changed'] = True
            if not module.check_mode:
                post_result = tet_module.run_method(
                    method_name='post',
                    target=TETRATION_API_AGENT_NAT_CONFIG,
                    req_payload=new_object,
                )
                result['object'] = post_result
            else:
                result['object'] = new_object
        # if the object does exist, check to see if any part of it should be
        # changed
        else:
            result['changed'] = False
            result['object'] = existing_object
    
    # ---------------------------------
    # STATE == 'absent'
    # ---------------------------------

    elif state == 'absent':
        if not existing_object:
            result['changed'] = False
        else:
            if not module.check_mode:
                tet_module.run_method(
                    method_name='delete',
                    target='%s/%s' % (TETRATION_API_AGENT_NAT_CONFIG, existing_object['id'])
                )
            result['changed'] = True
        result['object'] = None

    # ---------------------------------
    # STATE == 'query'
    # ---------------------------------

    elif state == 'query':
        result['object'] = existing_object

    # Return result
    module.exit_json(**result)

if __name__ == '__main__':
    main()
