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
description: Enables creation, modification, deletion and query of an agent interface
  config intent
extends_documentation_fragment: tetration
module: tetration_interface_intent
notes:
- Requires the tetpyclient Python module.
- Supports check mode.
options:
  inventory_filter_id:
    description:
    - Inventory Filter ID
    - Mutually exclusive to C(inventory_filter_name)
    type: string
  inventory_filter_name:
    description:
    - Inventory Filter Name
    - Mutually exclusive to C(inventory_filter_id)
    type: string
  query_type:
    choices: '[single, all]'
    default: single
    description: Options for expanding query search
    type: string
  state:
    choices: '[present, absent, query]'
    description: Add, change, remove or query for interface config intents
    required: true
    type: string
  vrf_id:
    description:
    - VRF ID integer
    - Mutually exclusive to C(vrf_name)
    type: string
  vrf_name:
    description:
    - VRF Name
    - Mutually exclusive to C(vrf_id)
    type: string
requirements: tetpyclient
version_added: '2.8'
'''

EXAMPLES = r'''
# Add or Modify interface config intent
tetration_interface_intent:
    vrf_name: ACME
    inventory_filter_name: ACME Filter
    state: present
    provider:
      host: "tetration-cluster@company.com"
      api_key: 1234567890QWERTY
      api_secret: 1234567890QWERTY

# Delete interface config intent
tetration_interface_intent:
    vrf_name: ACME
    inventory_filter_name: ACME Filter
    state: absent
    provider:
      host: "tetration-cluster@company.com"
      api_key: 1234567890QWERTY
      api_secret: 1234567890QWERTY

# Query for interface config intent
tetration_interface_intent:
    vrf_name: ACME
    inventory_filter_name: ACME Filter
    state: query
    provider:
      host: "tetration-cluster@company.com"
      api_key: 1234567890QWERTY
      api_secret: 1234567890QWERTY
'''

RETURN = r'''
---
object:
  contains:
    inventory_filter:
      description: Inventory filter dictionary
      returned: always
      sample: Inventory Filter JSON
      type: dict
    inventory_filter_id:
      description: Unique id of the filter associated with intent
      returned: always
      sample: 5c493b58755f027da9818750
      type: int
    vrf_id:
      description: VRF ID integer
      returned: always
      sample: 5c93da83497d4f33d7145960
      type: int
    vrf_name:
      description: VRF Name
      returned: always
      sample: ACME
      type: string
  description: the changed or modified object
  returned: always
  type: complex
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.tetration.api import TetrationApiModule
from ansible.module_utils.tetration.api import TETRATION_API_INTERFACE_INTENTS
from ansible.module_utils.tetration.api import TETRATION_API_TENANT
from ansible.module_utils.tetration.api import TETRATION_API_INVENTORY_FILTER
from ansible.module_utils.tetration.api import TETRATION_API_SCOPES

from ansible.utils.display import Display
display = Display()

def main():
    tetration_spec=dict(
        vrf_name=dict(type='str', required=False),
        vrf_id=dict(type='str', required=False),
        inventory_filter_id=dict(type='str', required=False),
        inventory_filter_name=dict(type='str', required=False),
        query_type=dict(type='str', required=False, choices=['single', 'all'], default='single'),
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
        mutually_exclusive=[
            ['vrf_name', 'vrf_id'],
            ['inventory_filter_name', 'inventory_filter_id']
        ]
    )

    tet_module = TetrationApiModule(module)

    # These are all elements we put in our return JSON object for clarity
    result = dict(
        changed=False,
        object=None,
    )

    state = module.params['state']
    vrf_name = module.params['vrf_name']
    vrf_id = module.params['vrf_id']
    inventory_filter_name = module.params['inventory_filter_name']
    inventory_filter_id = module.params['inventory_filter_id']
    app_scope = 'Default'
    query_type = module.params['query_type']
    current_intents = []
    target_object_index = None

    if state != 'query' or query_type != 'all':
        if not (vrf_name or vrf_id):
            module.fail_json(msg='One of the following parameters is required: vrf_name or vrf_id')
        if not (inventory_filter_name or inventory_filter_id):
            module.fail_json(msg='One of the following parameters is required: inventory_filter_name or inventory_filter_id')

    # =========================================================================
    # Get current state of the object

    # Get VRF ID if name passed
    if not vrf_id:
        vrf_object = tet_module.get_object(
            target = TETRATION_API_TENANT,
            filter = dict(name=vrf_name)
        )
        vrf_id = None if vrf_object is None else vrf_object['id']
    if not vrf_id and state != 'query':
        module.fail_json(msg='A VRF could not be found matching name: %s' % vrf_name)
    # Get inventory filter id if name is passed
    if not inventory_filter_id:
        scope_object = tet_module.get_object(
            target = TETRATION_API_SCOPES,
            filter = dict(name=app_scope)
        )
        if not scope_object:
            module.fail_json(msg='An app scope cannot be found with name: %s' % app_scope)
        app_scope_id = scope_object['id']

        filter_object = tet_module.get_object(
            target = TETRATION_API_INVENTORY_FILTER,
            filter = dict(name=inventory_filter_name,app_scope_id=app_scope_id)
        )
        inventory_filter_id = None if filter_object is None else filter_object['id']
    if not inventory_filter_id and state != 'query':
        module.fail_json(msg='An inventory filter could not be found matching name: %s' % inventory_filter_name)
    # Get existing interface config intent if exists
    current_intents = tet_module.run_method(
        method_name='get',
        target=TETRATION_API_INTERFACE_INTENTS
        )
    current_intents =  list(current_intents['intents']) if current_intents else []
    for idx, intent in enumerate(current_intents):
        if intent['vrf_id'] == vrf_id:
            target_object_index = idx
            if intent['inventory_filter_id'] != inventory_filter_id:
                result['changed'] = True
            break

    # =========================================================================
    # Now enforce the desired state (present, absent, query)

    # ---------------------------------
    # STATE == 'present'
    # ---------------------------------
    if state == 'present':
        # if the object does not exist at all, create it
        new_object = dict(
            vrf_id=vrf_id, 
            inventory_filter_id=inventory_filter_id, 
        )
        if not (target_object_index >= 0) or result['changed']:
            if not result['changed']:
                result['changed'] = True
                current_intents.append(new_object)
            else:
                current_intents[target_object_index] = new_object
            if not module.check_mode:
                post_result = tet_module.run_method(
                    method_name='post',
                    target=TETRATION_API_INTERFACE_INTENTS,
                    req_payload=dict(intents=current_intents),
                )
                result['object'] = tet_module.run_method(
                    method_name='get',
                    target=TETRATION_API_INTERFACE_INTENTS
                    )
            else:
                filter_object = tet_module.get_object(
                    target = TETRATION_API_INVENTORY_FILTER,
                    filter = dict(id=inventory_filter_id)
                )
                vrf_object = tet_module.get_object(
                    target = TETRATION_API_TENANT,
                    filter = dict(id=vrf_id)
                )
                current_intents[-1]['inventory_filter'] = filter_object
                current_intents[-1]['vrf_name'] = vrf_object['name']
                result['object'] = current_intents

        # if the object does exist, check to see if any part of it should be
        # changed
        else:
            result['changed'] = False
            result['object'] = current_intents
    
    # ---------------------------------
    # STATE == 'absent'
    # ---------------------------------

    elif state == 'absent':
        if target_object_index >= 0 and not result['changed']:
            result['changed'] = True
            del current_intents[target_object_index]
            if not module.check_mode:
                post_result = tet_module.run_method(
                    method_name='post',
                    target=TETRATION_API_INTERFACE_INTENTS,
                    req_payload=dict(intents=current_intents),
                )
            result['object'] = current_intents
        elif result['changed']:
            module.fail_json(msg='Inventory filter id %s does not match current filter associated with vrf %s config intent' % (inventory_filter_id, vrf_id))
        else:
            result['object'] = current_intents


    # ---------------------------------
    # STATE == 'query'
    # ---------------------------------

    elif state == 'query':
        # we already retrieved the current state of the object, so there is no
        # need to do it again
        if query_type == 'single':
            result['object'] = current_intents[target_object_index] if target_object_index >= 0 else None
        else:
            result['object'] = current_intents

    # Return result
    module.exit_json(**result)

if __name__ == '__main__':
    main()
