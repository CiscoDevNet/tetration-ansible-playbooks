#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2018, Doron Chosnek
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
import time
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
author: Doron Chosnek (@dchosnek)
description:
- Enables management of Cisco Tetration user accounts.
- Enables creation, modification, and deletion of accounts.
- Capabilities can be added to the user account, but they cannot be deleted.
extends_documentation_fragment: tetration
module: tetration_user
notes:
- Requires the tetpyclient Python module.
- Supports check mode.
options:
  app_scope_id:
    description: ID of the user scope. Omit this parameter or set it to an empty string
      to create a user not limited to one scope (most people will want to do this).
      Scope ID and scope name are mutually exclusive.
    type: string
  app_scope_name:
    description: Name of the root scope in which to place the user. Omit this parameter
      or set it to an empty string to create a user not limited to one scope. Scope
      ID and scope name are mutually exclusive.
    type: string
  email:
    description: User email address (must be unique within Tetration)
    required: true
    type: string
  first_name:
    description: User first name is only required when creating a new user. This parameter
      can optionally be used to change the first name of an existing user.
    type: string
  last_name:
    description: User last name is only required when creating a new user. This parameter
      can optionally be used to change the last name of an existing user.
    type: string
  state:
    choices: '[present, absent, query]'
    description: Add, change, remove or search for the user
    required: true
    type: string
requirements: tetpyclient
short_description: Manage user accounts
version_added: '2.8'
'''

EXAMPLES = r'''
# Create new user or update first/last name of existing user
- tetration_user:
    provider: "{{ my_tetration }}"
    email: bsmith@example.com
    first_name: Bob
    last_name: Smith
    state: present

# Move user to the specified root scope
- tetration_user:
    provider: "{{ my_tetration }}"
    email: bsmith@example.com
    state: present
    app_scope_name: Default

# Get details for existing user, including what roles are 
# assigned to that user
- tetration_user:
    provider: "{{ my_tetration }}"
    email: bsmith@example.com
    state: query

# Disable a user (Tetration users are never really deleted)
- tetration_user:
    provider: "{{ my_tetration }}"
    email: bsmith@example.com
    state: absent
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
from ansible.module_utils.tetration.api import TETRATION_API_SCOPES


def main():
    tetration_spec=dict(
        first_name=dict(type='str', required=False),
        last_name=dict(type='str', required=False),
        email=dict(type='str', required=True),
        app_scope_id=dict(type='str', required=False),
        app_scope_name=dict(type='str', required=False),
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
            ['app_scope_id', 'app_scope_name']
        ]
    )

    tet_module = TetrationApiModule(module)

    # These are all elements we put in our return JSON object for clarity
    result = dict(
        failed=False,
        object=None,
    )

    state = module.params['state']
    email = module.params['email']
    first_name = module.params['first_name']
    last_name = module.params['last_name']
    app_scope_id = module.params['app_scope_id']
    app_scope_name = module.params['app_scope_name']

    # =========================================================================
    # Get current state of the object

    # The first thing we have to do is get the object.
    existing_object = tet_module.get_object(
        target = TETRATION_API_USER,
        params=dict(include_disabled='true'),
        filter = dict(email=email),
    )
    disabled_user = False if existing_object is None or existing_object['disabled_at'] is None else True
    id = None if existing_object is None else existing_object['id']
    
    # =========================================================================
    # Now enforce the desired state (present, absent, query)
 
    # at this point in the code, there will be one object stored in the
    # variable named existing_object
    changed = False

    # ---------------------------------
    # STATE == 'present'
    # ---------------------------------
    if state == 'present':

        new_object = dict(email=email)
        if first_name is not None:
            new_object['first_name'] = first_name
        if last_name is not None:
            new_object['last_name'] = last_name
        if app_scope_id is not None:
            new_object['app_scope_id'] = app_scope_id
        # Get the app scope id if name is passed
        if app_scope_name:
            app_scope = tet_module.get_object(
                target = TETRATION_API_SCOPES,
                filter = dict(name=app_scope_name)
            )
            if app_scope is None or ':' in app_scope_name:
                error_message = (
                    'You specified an app scope name that does not exist. Try '
                    'again with a valid name or exclude both app_scope_name '
                    'and app_scope_id to create a Service Provider user. Only '
                    'root scopes are allowed. For example, Default is valid '
                    'but Default:Datacenter is not a valid scope name for '
                    'user accounts.'
                )
                module.fail_json(msg=error_message)
            else:
                new_object['app_scope_id'] = app_scope['id']
                module.params['app_scope_id'] = app_scope['id']

        # if the object does not exist at all, create it
        if not existing_object:
            changed = True
            if not module.check_mode:
                query_result = tet_module.run_method(
                    method_name='post',
                    target=TETRATION_API_USER,
                    req_payload=new_object,
                )
                id = query_result['id']

        # if the object does exist, check to see if any part of it should be
        # changed
        else:
            # if the user is inactive, then reactivate
            if disabled_user:
                changed = True
                tet_module.run_method(
                    method_name='post',
                    target='%s/%s/enable' % (TETRATION_API_USER, id),
                )

            # if name or app_scope_id don't match, UPDATE!
            update_needed = False
            for k in ['first_name', 'last_name', 'app_scope_id']:
                if module.params[k] is not None and existing_object[k] != module.params[k]:
                    update_needed = True
            if update_needed:
                changed = True
                if not module.check_mode:
                    tet_module.run_method(
                        method_name='put',
                        target='%s/%s' % (TETRATION_API_USER, id),
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
                    target='%s/%s' % (TETRATION_API_USER, id)
                )
            result['object'] = query_result
    
    # ---------------------------------
    # STATE == 'absent'
    # ---------------------------------

    elif state == 'absent':
        # if existing_object is a non-empty dictionary, that means there is
        # something to delete; if it's empty then there is nothing to do
        if bool(existing_object) and not disabled_user:
            changed = True
            if module.check_mode:
                existing_object['disabled_at'] = int(time.time())
            else:
                tet_module.run_method(
                    method_name='delete',
                    target='%s/%s' % (TETRATION_API_USER, id)
                )
                # there is no way to retrieve an individual user directly
                # by ID; we have to retrieve all users and filter for the
                # one with the right email address
                existing_object = tet_module.get_object(
                    target = TETRATION_API_USER,
                    params=dict(include_disabled='true'),
                    filter = dict(email=email),
                )
        result['object'] = existing_object
    
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
