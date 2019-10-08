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
module: tetration_rest
version_added: 2.67
short_description: Direct access to the Cisco Tetration REST API
description:
   - Enables the management of the Cisco Tetration platform through direct access to the
     REST API.
   - Can perform GET, POST, PUT or DELETE operations against any Tetration API name.
   - Does not validate that an name exists or operation is allowed. Error messages
     will be returned in both cases.
   - Cannot always properly identify if a call will make a change to Tetration. For accurate
     change status, use dedicated Ansible modules for each Tetration API rather than this
     generic REST module.
notes:
   - Requires the tetpyclient Python module. Use pip install tetpyclient to install it.
author:
    - Doron Chosnek (@dchosnek)
requirements:
    - tetpyclient
options:
  api_key:
    description:
    - The API key for the key/secret combination.
    required: yes
  api_secret:
    description:
    - The API secret for the key/secret combination.
    required: yes
  api_version:
    description:
    - The default is v1.
    - Allows for future releases of other versions of the API.
    required: no
    default: v1
  name:
    description:
    - The API target to access.
    - Examples: users, vrfs, scopes, roles
    required: yes
  method:
    description:
    - The HTTP method of the request.
    required: yes
    choices: [get, post, put, delete]
  host:
    description:
    - The URL of the Tetration system.
    required: yes
  payload:
    description:
    - A dict of values to be used for PUT and POST operations.
    - This value is ignored for GET and DELETE.
    required: no
'''

EXAMPLES = r'''
# Test we can logon to 'webservers' and execute python with json lib.
# ansible webservers -m ping

# Example from an Ansible Playbook
- ping:

# Induce an exception to see what happens
- ping:
    data: crash
'''

RETURN = r'''
ping:
    description: value provided with the data parameter
    returned: success
    type: string
    sample: pong
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.tetration.api import TetrationApiModule
from ansible.module_utils.tetration.api import TETRATION_API_USER
from ansible.module_utils.tetration.api import TETRATION_API_SCOPES
import json


def main():
    tetration_spec=dict(
        user_id=dict(type='str', required=False),
        first_name=dict(type='str', required=False),
        last_name=dict(type='str', required=False),
        email=dict(type='str', required=True),
        app_scope_id=dict(type='str', required=False),
        app_scope_name=dict(type='str', required=False),
        reuse_domain=dict(type='str', required=False, default=None)
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
    available_user_account = None
    reuse_domain = module.params['reuse_domain']
    user_id = module.params['user_id']
    existing_user = None

    # =========================================================================
    # Get current state of the object

    # The first thing we have to do is get the object.

    if user_id:
        existing_user = tet_module.run_method(
            method_name = 'get',
            target = '%s/%s' % (TETRATION_API_USER, user_id)
        )

        if not existing_user:
            module.fail_json(msg='Unable to find user with id: %s' % user_id)
        disabled_user = False if existing_user['disabled_at'] is None else True
    else:
        all_users = tet_module.run_method(
            method_name='get',
            target='%s' % (TETRATION_API_USER),
            params=dict(include_disabled='true'),
        )

        for obj in all_users:
            if obj['email'] == email:
                existing_user = obj
                disabled_user = False if obj['disabled_at'] is None else True
                break
            elif not available_user_account and obj['disabled_at'] and reuse_domain and reuse_domain in obj['email']:
                available_user_account = obj

    
    # =========================================================================
    # Now enforce the desired state (present, absent, query)
 
    # at this point in the code, there will be one object stored in the
    # variable named existing_user
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

        # if the object does not exist at all, create it
        if not existing_user:
            changed = True
            # Get the app scope id if name is passed
            if not app_scope_id and app_scope_name:
                app_scope = tet_module.get_object(
                    target = TETRATION_API_SCOPES,
                    filter = dict(name=app_scope_name)
                )
                new_object['app_scope_id'] = None if app_scope is None else app_scope['id']
            if not module.check_mode:
                if available_user_account:
                    # Re-enable disabled account
                    tet_module.run_method(
                        method_name='post',
                        target='%s/%s/enable' % (TETRATION_API_USER, available_user_account['id']),
                        req_payload=new_object
                    )
                    # update disabled blank user account with new user details
                    tet_module.run_method(
                        method_name='put',
                        target='%s/%s' % (TETRATION_API_USER, available_user_account['id']),
                        req_payload=new_object
                    )
                    user_id = available_user_account['id']
                else:
                    query_result = tet_module.run_method(
                        method_name='post',
                        target=TETRATION_API_USER,
                        req_payload=new_object,
                    )
                    user_id = query_result['id']

        # if the object does exist, check to see if any part of it should be
        # changed
        else:
            # if the user is inactive, then reactivate
            user_id = user_id if user_id else existing_user['id']
            if disabled_user:
                changed = True
                tet_module.run_method(
                    method_name='post',
                    target='%s/%s/enable' % (TETRATION_API_USER, existing_user['id']),
                )

            # if email, name, or app_scope_id don't match, UPDATE!
            update_needed = False
            for k in ['email', 'first_name', 'last_name', 'app_scope_id']:
                if module.params[k] is not None and existing_user[k] != module.params[k]:
                    update_needed = True
            if update_needed:
                changed = True
                if not module.check_mode:
                    tet_module.run_method(
                        method_name='put',
                        target='%s/%s' % (TETRATION_API_USER, existing_user['id']),
                        req_payload=new_object,
                    )

        # decide what value to return
        if not changed:
            result['object'] = existing_user
        elif module.check_mode:
            result['object'] = new_object
        else:
            # retrieve the current state of the object
            query_result = tet_module.run_method(
                    method_name='get',
                    target='%s/%s' % (TETRATION_API_USER, user_id)
                )
            result['object'] = query_result
    
    # ---------------------------------
    # STATE == 'absent'
    # ---------------------------------

    elif state == 'absent':
        # if existing_user is a non-empty dictionary, that means there is
        # something to delete; if it's empty then there is nothing to do
        if bool(existing_user) and not disabled_user:
            changed = True
            if not module.check_mode:
                if reuse_domain:
                    # update disabled blank user account with new user details
                    tet_module.run_method(
                        method_name='put',
                        target='%s/%s' % (TETRATION_API_USER, existing_user['id']),
                        req_payload=dict(
                            email='%s@%s' % (existing_user['id'], reuse_domain)
                        )
                    )
                    result['object'] = dict(id=existing_user['id'])
                tet_module.run_method(
                    method_name='delete',
                    target='%s/%s' % (TETRATION_API_USER, existing_user['id'])
                )
            result['object'] = existing_user
    
    # ---------------------------------
    # STATE == 'query'
    # ---------------------------------

    elif state == 'query':
        # we already retrieved the current state of the object, so there is no
        # need to do it again
        result['object'] = existing_user


    module.exit_json(changed=changed, **result)

if __name__ == '__main__':
    main()
