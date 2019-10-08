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
- Enables management of Cisco Tetration roles.
- Enables creation, modification, and deletion of roles.
- Can add capabilities to a role, but cannot modify or delete capabilities.
extends_documentation_fragment: tetration
module: tetration_role
notes:
- Requires the tetpyclient Python module.
- Supports check mode.
options:
  app_scope_id:
    default: '""'
    description: ID of the scope where the role exists. An empty string means it is
      a service provider role.
    type: string
  capability_ability:
    choices: '[read, write, execute, developer, enforce, owner]'
    description: The name of the ability assigned to a role. Multiple abilities can
      be assigned to a role with a loop. Abilities can be added but cannot be removed
      from a role. Capability_appscope and capability_ability are not required parameters
      but must be specified together.
    type: string
  capability_appscope:
    description: ID of the scope in which the capability has abilities
    type: string
  description:
    description: description of the role
    type: string
  id:
    description: GUID for the role to be altered or deleted. Must specify either id
      or name and app_scope_id.
    type: string
  name:
    description: Name of the role. Must specify either id or name and app_scope_id.
    type: string
  state:
    choices: '[present, absent, query]'
    description: Add, change, remove or search for the role
    required: true
    type: string
requirements: tetpyclient
short_description: Manage roles and capabilities
version_added: '2.8'
'''

EXAMPLES = r'''
  # Query an existing role by name (query can be done by name or ID)
  - tetration_role:
      provider: "{{ my_tetration }}"
      name: expenses app owner
      state: query

  # Create or modify an existing role that has read access to the specified scope.
  # You can create a role with no capabilities, but that would not be useful.
  - tetration_role:
      provider: "{{ my_tetration }}"
      name: expenses app reader
      description: read only access to the expenses application
      state: present
      capability_ability: read
      capability_appscope: "{{ expenses_app_scope }}"

  # Set description of a role (name can also be changed when you specify the ID of the role) 
  - tetration_role:
      provider: "{{ my_tetration }}"
      id: "{{ expenses_reader.object.id }}"
      description: modified name and desc for app reader
      state: present

  # All of the above examples can be done to roles inside an app scope 
  # by specifying the app_scope_id variable
  - tetration_role:
      provider: "{{ my_tetration }}"
      name: app reader subscope
      description: role in a subscope
      app_scope_id: "{{ default_scope }}"
      state: present

  # Add multiple capabilities to a role using loop
  - tetration_role:
      provider: "{{ my_tetration }}"
      name: expenses app owner
      state: present
      capability_ability: "{{ item.ability }}"
      capability_appscope: "{{ item.scope }}"
    loop:
    - { scope: "{{ expenses_app_scope }}", ability: 'execute' }
    - { scope: "{{ expenses_app_scope }}", ability: 'developer' }

  # Delete a role by name
  - tetration_role:
      provider: "{{ my_tetration }}"
      name: expenses app owner
      state: absent
'''

RETURN = r'''
---
object:
  contains:
    app_scope_id:
      description: Scope to which the scope is defined, maybe empty for Service Provider
        Roles.
      returned: when C(state) is present or query
      sample: '""'
      type: string
    capabilities:
      description: List of capabilities. Each capability specifies ability, app_scope_id,
        id, inherited, and role_id.
      returned: when C(state) is present or query and the role has capabilities
      type: list
    description:
      description: User specified description for the role.
      returned: when C(state) is present or query
      sample: allows for reading of the expenses application
      type: string
    id:
      description: Unique identifier for the role.
      returned: when C(state) is present or query
      sample: 5bc0bb14497d4f143b7ca660
      type: string
    name:
      description: User specified name for the role.
      returned: when C(state) is present or query
      sample: Expenses App Reader
      type: string
  description: the changed or modified object
  returned: always
  type: complex
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.tetration.api import TetrationApiModule
from ansible.module_utils.tetration.api import TETRATION_API_ROLE


def main():
    tetration_spec=dict(
        name=dict(type='str', required=False),
        description=dict(type='str', required=False),
        app_scope_id=dict(type='str', required=False, default=""),
        id=dict(type='str', required=False),
        capability_appscope=dict(type='str', required=False),
        capability_ability=dict(type='str', required=False, 
            choices=['read', 'write', 'execute', 'developer', 'enforce', 'owner'])
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
        required_one_of=[ ['name', 'id'] ],
        required_together=[ ['capability_appscope', 'capability_ability'] ],
    )

    tet_module = TetrationApiModule(module)

    # These are all elements we put in our return JSON object for clarity
    result = dict(
        failed=False,
        object=None,
    )


    CAPABILITIES = {
        'read': 'SCOPE_READ',
        'write': 'SCOPE_WRITE',
        'execute': 'EXECUTE',
        'developer': 'DEVELOPER',
        'enforce': 'ENFORCE',
        'owner': 'SCOPE_OWNER',
    }

    state = module.params['state']
    scope = module.params['app_scope_id']
    name = module.params['name']
    description = module.params['description']
    id = module.params['id']


    # =========================================================================
    # Get current state of the object

    # The first thing we have to do is get the object.
    existing_object = dict()
    
    # if the user specified an ID, search for that ID
    if id is not None:

        # First ensure the ID exists to avoid errors in update and delete.
        # Without this step, both the GET and DELETE operations would fail
        # attempting to operate on an invalid ID.
        existing_object = tet_module.get_object(
            target = TETRATION_API_ROLE,
            filter = dict(id=id),
        )

        # if it exists, then perform a GET on that ID to get the full details
        if existing_object:
            existing_object = tet_module.run_method(
                method_name='get',
                target='%s/%s' % (TETRATION_API_ROLE, id),
            )
        # if it doesn't exist, and the state=present, that is an error
        elif state == 'present':
            error_message = (
                'The ID specified does not exist. To create a new object, do '
                'not specify an ID as Tetration will assign one to every new '
                'object.'
            )
            module.fail_json(msg=error_message)
    
    # if the user specified a name, search for that name
    elif name is not None:

        # name alone is not unique, but name and app_scope_id is unique
        existing_object = tet_module.get_object(
            target = TETRATION_API_ROLE,
            filter = dict(name=name, app_scope_id=scope),
        )
        # need to get the full object, complete with its capabilties
        if existing_object is not None:
            id = existing_object['id']
            existing_object = tet_module.run_method(
                method_name='get',
                target='%s/%s' % (TETRATION_API_ROLE, id),
            )

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
        if description is not None:
            new_object['description'] = description
        if name is not None:
            new_object['name'] = name

        # if the object does not exist at all, create it
        if not existing_object:
            changed = True
            if scope != "":
                new_object['app_scope_id'] = scope
            if not module.check_mode:
                query_result = tet_module.run_method(
                    method_name='post',
                    target=TETRATION_API_ROLE,
                    req_payload=new_object,
                )
                id = query_result['id']

        # if the object does exist, check to see if any part of it should be
        # changed
        else:
            # if the name or description don't match, update the role
            if (name is not None and existing_object['name'] != name) or (description is not None and existing_object['description'] != description):
                changed = True
                if not module.check_mode:
                    tet_module.run_method(
                        method_name='put',
                        target='%s/%s' % (TETRATION_API_ROLE, id),
                        req_payload=new_object,
                    )

        # now we need to see if we should add the capabilities specified
        if module.params['capability_ability'] is not None:
            my_ability = CAPABILITIES[module.params['capability_ability']]
            my_scope = module.params['capability_appscope']
            if existing_object and 'capabilities' in existing_object:
                t = [ (obj['ability'], obj['app_scope_id']) for obj in existing_object['capabilities'] ]
            else:
                t = []
            if (my_ability, my_scope) not in t:
                changed = True
                if not module.check_mode:
                    req_payload = { "app_scope_id": my_scope, "ability": my_ability }
                    tet_module.run_method(
                        method_name='post',
                        target='%s/%s/capabilities' % (TETRATION_API_ROLE, id),
                        req_payload=req_payload,
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
                    target='%s/%s' % (TETRATION_API_ROLE, id)
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
                    target='%s/%s' % (TETRATION_API_ROLE, id)
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
