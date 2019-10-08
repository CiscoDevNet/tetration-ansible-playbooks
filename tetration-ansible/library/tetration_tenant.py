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
author: Doron Chosnek (@dchosnek)
description:
- Enables management of Cisco Tetration tenants.
- Enables creation, modification, and deletion of tenants.
- VRFs can be added or removed from an existing tenant.
extends_documentation_fragment: tetration
module: tetration_tenant
notes:
- Requires the tetpyclient Python module.
- Supports check mode.
options:
  id:
    description: ID of the tenant. Can be used to query, modify, or delete a tenant,
      but Name is recommended instead.
    type: string
  name:
    description: Name of the tenant. Required when creating a new tenant.
    type: string
  state:
    choices: '[present, absent, query]'
    description: Add, change, or remove the tenant
    required: true
    type: string
  switch_vrfs:
    default: '[]'
    description: List of switch vrf names that map to this Tetration tenant
    type: list
requirements: tetpyclient
short_description: Manages Tetration tenants
version_added: '2.8'
'''

EXAMPLES = r'''
# Create a tenant
  - tetration_tenant:
      provider: "{{ my_tetration }}"
      name: First Tenant
      state: present
    register: first_tenant

# Modify existing tenant's name and VRFs
- tetration_tenant:
    provider: "{{ my_tetration }}"
    id: "{{ first_tenant.object.id }}"
    name: Engineering
    state: present
    switch_vrfs:
    - vrf1
    - vrf2
    - vrf3
    - etc

# Remove switch VRFs from tenant; the default value for switch_vrfs is an
# empty list, so leaving out that parameter essentially removes VRFs from
# this tenant
- tetration_tenant:
    provider: "{{ my_tetration }}"
    name: Engineering
    state: present

# Remove a tenant
- tetration_tenant:
    provider: "{{ my_tetration }}"
    name: Engineering
    state: absent
'''

RETURN = r'''
---
object:
  contains:
    created_at:
      description: Unix timestamp when the VRF was created.
      returned: when C(state) is present or query
      sample: 1539209291
      type: int
    id:
      description: Unique identifier for the tenant
      returned: when C(state) is present or query
      sample: 67000
      type: string
    name:
      description: User specified name for the tenant
      returned: when C(state) is present or query
      sample: Engineering
      type: string
    root_app_scope_id:
      description: ID of associated root scope.
      returned: when C(state) is present or query
      sample: 5bbe784b755f0254aa632f20
      type: string
    switch_vrfs:
      description: List of switch vrf names that map to this Tetration tenant
      returned: when C(state) is present or query
      sample: '["vrf1", "vrf2", "vrf3"]'
      type: list
    tenant_id:
      description: ID of parent tenant.
      returned: when C(state) is present or query
      sample: 67000
      type: int
    updated_at:
      description: Unix timestamp when the VRF was last updated.
      returned: when C(state) is present or query
      sample: 1539209291
      type: int
  description: the changed or modified object
  returned: always
  type: complex
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.tetration.api import TetrationApiModule
from ansible.module_utils.tetration.api import TETRATION_API_TENANT


def main():
    tetration_spec=dict(
        name=dict(type='str', required=False),
        id=dict(type='str', required=False),
        switch_vrfs=dict(type='list', required=False, default=[]),
        query_type=dict(type='str', choices=['single', 'all'], default='single')
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
          ['state', 'query', ['query_type']]
        ],
    )

    tet_module = TetrationApiModule(module)

    # These are all elements we put in our return JSON object for clarity
    result = dict(
        failed=False,
        object=None,
    )

    state = module.params['state']
    name = module.params['name']
    id = module.params['id']
    switch_vrfs = module.params['switch_vrfs']
    query_type = module.params.get('query_type')

    if state in ['present', 'absent'] and (not name and not id):
      module.fail_json(msg='Either name or id is required')

    # =========================================================================
    # Get current state of the object

    # The first thing we have to do is get the object.
    existing_object = dict()
    
    # if the user specified an ID, search for that ID
    if (state != 'query' or query_type == 'single') and id is not None:

        existing_object = tet_module.get_object(
            target = TETRATION_API_TENANT,
            filter = dict(id=int(id)),
        )
    
    # if the user specified a name, search for that name
    elif (state != 'query' or query_type == 'single') and name is not None:

        existing_object = tet_module.get_object(
            target = TETRATION_API_TENANT,
            filter = dict(name=name),
        )
        id = int(existing_object['id']) if existing_object else None

        # query_result = tet_module.run_method(
        #     method_name='get',
        #     target=TETRATION_API_TENANT,
        # )

        # # find the one Tenant/VRF whose name matches
        # for obj in query_result:
        #     if obj['name'] == name:
        #         id = obj['id']

        #         query_result = tet_module.run_method(
        #             method_name='get',
        #             target='%s/%s' % (TETRATION_API_TENANT, id),
        #         )
        #         existing_object = query_result
    elif state == 'query' and query_type == 'all':
      existing_object = tet_module.run_method(
            'get',
            target=TETRATION_API_TENANT
        )
      existing_object = [ tenant for tenant in existing_object if name not in ['Tetration', 'Unknown', 'Default']]
    # if ID is still not defined, then we need to create an ID for you
    if id is None:
        query_result = tet_module.run_method(
            method_name='get',
            target=TETRATION_API_TENANT,
        )
        existing_ids = [ x['id'] for x in query_result ]
        id = 676769
        while id in existing_ids:
            id -= 1

    
    # =========================================================================
    # Now enforce the desired state (present, absent, query)
 
    # at this point in the code, there will be one object stored in the
    # variable named existing_object
    changed = False

    # ---------------------------------
    # STATE == 'present'
    # ---------------------------------
    if state == 'present':

        new_object = dict()
        if switch_vrfs is not None:
            new_object['switch_vrfs'] = switch_vrfs
        if name is not None:
            new_object['name'] = name

        # if the object does not exist at all, create it
        if not existing_object:
            changed = True
            new_object['id'] = id
            if not module.check_mode:
                query_result = tet_module.run_method(
                    method_name='post',
                    target=TETRATION_API_TENANT,
                    req_payload=new_object,
                )
                id = query_result['id']

        # if the object does exist, check to see if any part of it should be
        # changed
        else:
            # if the name or switch VRFs don't match, update the role
            if (name is not None and existing_object['name'] != name) or (switch_vrfs is not None and set(existing_object['switch_vrfs']) != set(switch_vrfs)):
                changed = True
                if not module.check_mode:
                    tet_module.run_method(
                        method_name='put',
                        target='%s/%s' % (TETRATION_API_TENANT, id),
                        req_payload=new_object,
                    )

        # decide what value to return
        if not changed:
            result['object'] = existing_object
        elif module.check_mode:
            result['object'] = new_object
        else:
            # retrieve the current state of the object
            query_result = tet_module.run_method(
                    method_name='get',
                    target='%s/%s' % (TETRATION_API_TENANT, id)
                )
            result['object'] = query_result
    
    # ---------------------------------
    # STATE == 'absent'
    # ---------------------------------

    elif state == 'absent':
        # if existing_object is a non-empty dictionary, that means there is
        # something to delete; if it's empty then there is nothing to do
        if bool(existing_object):
            changed = True
            if not module.check_mode:
                tet_module.run_method(
                    method_name='delete',
                    target='%s/%s' % (TETRATION_API_TENANT, id)
                )
    
    # ---------------------------------
    # STATE == 'query'
    # ---------------------------------

    elif state == 'query':
        # we already retrieved the current state of the object, so there is no
        # need to do it again
        result['object'] = existing_object



    module.exit_json(changed=changed, **result)

if __name__ == '__main__':
    main()
