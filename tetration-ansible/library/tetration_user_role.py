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
- Enables management of roles attached to Cisco Tetration users.
- Enables addition or deletion of roles from a user account.
extends_documentation_fragment: tetration
module: tetration_user_role
notes:
- Requires the tetpyclient Python module.
- Supports check mode.
options:
  email:
    description: User email address
    required: true
    type: string
  role_ids:
    description: List of IDs of roles to add or remove from user
    required: true
    type: string
  state:
    choices: '[present, absent]'
    description: Add or remove roles
    required: true
    type: string
requirements: tetpyclient
short_description: Manage roles assigned to user accounts
version_added: '2.8'
'''

EXAMPLES = r'''
  # The next two tasks combined will remove all roles from the specified user
  - name: Query user to see what roles are attached
    tetration_user:
      provider: "{{ my_tetration }}"
      email: bsmith@example.com
      state: query
    register: my_user

  - name: Remove all roles from the user
    tetration_user_role:
      provider: "{{ my_tetration }}"
      email: "{{ my_user.object.email }}"
      state: absent
      role_ids: "{{ my_user.object.role_ids }}"
    register: empty_user

  # Add a few roles to an existing user
  - tetration_user_role:
      provider: "{{ my_tetration }}"
      email: bsmith@example.com
      state: present
      role_ids:
      - 5bb7bc06497d4f231c3bd48d
      - 5bc0bb14497d4f143b7ca660
      - 5bcbe0ab755f025f87632f2b
'''

RETURN = r'''
---
object:
  contains:
    app_scope_id:
      description: The scope to which the user is assigned. Maybe empty if the user
        is a Service Provider User.
      returned: always
      sample: '""'
      type: string
    created_at:
      description: Unix timestamp of when the user was created.
      returned: always
      sample: '1541993885.0'
      type: int
    disabled_at:
      description: Unix timestamp of when the user has been disabled. Zero or null,
        otherwise.
      returned: always
      sample: 'null'
      type: int
    email:
      description: Email associated with user account.
      returned: always
      sample: bsmith@example.com
      type: string
    first_name:
      description: First name.
      returned: always
      sample: Bob
      type: string
    id:
      description: Unique identifier for the user role.
      returned: always
      sample: 5bb7eaa3497d4f4e657ca65a
      type: string
    last_name:
      description: Last name.
      returned: always
      sample: Smith
      type: string
    role_ids:
      description: List of IDs of roles assigned to the user account.
      returned: always
      sample: '[ "5bb7bc06497d4f231c3bd481", "5bb7bc06497d4f231c3bd481" ]'
      type: string
  description: the changed or modified object
  returned: always
  type: complex
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.tetration.api import TetrationApiModule
from ansible.module_utils.tetration.api import TETRATION_API_USER
from ansible.module_utils.tetration.api import TETRATION_API_ROLE


def main():
    tetration_spec=dict(
        email=dict(type='str', required=True),
        role_ids=dict(type='list', required=True),
    )

    argument_spec = dict(
        provider=dict(required=True),
        state=dict(required=True, choices=['present', 'absent'])
    )

    argument_spec.update(tetration_spec)
    argument_spec.update(TetrationApiModule.provider_spec)

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    tet_module = TetrationApiModule(module)

    # These are all elements we put in our return JSON object for clarity
    result = dict(
        failed=False,
        object=None,
    )

    state = module.params['state']
    email = module.params['email']
    requested_list = module.params['role_ids']


    # =========================================================================
    # Get current state of the object

    existing_object = tet_module.get_object(
        target = TETRATION_API_USER,
        # params=dict(include_disabled='true'),
        filter = dict(email=email),
    )
    if bool(existing_object):
        id = existing_object['id']
        existing_list = existing_object['role_ids']
    else:
        error_message = (
            'The user whose email address you specified does not exist or is '
            'disabled. Roles cannot be added or removed from a disabled or '
            'nonexistent user.'
        )
        module.fail_json(msg=error_message)

    
    # =========================================================================
    # Now enforce the desired state (present, absent)
 
    changed = False

    # ---------------------------------
    # STATE == 'present'
    # ---------------------------------
    if state == 'present':

        # step through the list and add all roles that don't already exist
        for role in requested_list:
            if role not in existing_list:
                changed = True
                if not module.check_mode:
                    tet_module.run_method(
                        method_name='put',
                        target='%s/%s/add_role' % (TETRATION_API_USER, id),
                        req_payload=dict(role_id=role),
                    )
    
    # ---------------------------------
    # STATE == 'absent'
    # ---------------------------------

    elif state == 'absent':
        active_roles = tet_module.run_method(
            method_name = 'get',
            target = TETRATION_API_ROLE
        )
        active_role_ids = [ role['id'] for role in active_roles ]
        # step through the list and remove all roles that exist
        for role in requested_list:
            if role in existing_list:
                changed = True
                if not module.check_mode and role in active_role_ids:
                    tet_module.run_method(
                        method_name='delete',
                        target='%s/%s/remove_role' % (TETRATION_API_USER, id),
                        req_payload=dict(role_id=role),
                    )

    # ---------------------------------
    # fetch current state to return
    # ---------------------------------

    query_result = tet_module.run_method(
        method_name='get',
        target='%s/%s' % (TETRATION_API_USER, id),
    )
    result['object'] = query_result

    module.exit_json(changed=changed, **result)

if __name__ == '__main__':
    main()
