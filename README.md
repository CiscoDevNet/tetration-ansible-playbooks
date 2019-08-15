# Ansible Cisco Tetration Playbooks

Cisco Tetration offers holistic workload protection for multi-cloud data centers by enabling a zero-trust model using segmentation. This approach allows the identification of security incidents faster, contains lateral movement, and reduces the  attack surface. Tetration's infrastructure-agnostic approach supports both on-premises and public cloud workloads.

These Ansible playbooks and supporting files enable the querying and display of various aspects of Cisco Tetration.

## Resources

Theses Ansible playbook were created using Cisco dCloud [Cisco Tetration Platform 3.1 v1](https://dcloud2-rtp.cisco.com/#) instant-access environment.  The playbooks map directly to scenarios outlined in the [documentation](https://dcloud2-rtp.cisco.com/#).

## Scenarios

- Scenario 1 - This playbook queries the applications, scopes and inventory search API endpoints. Execute the playbook with -v to view all the API returned data.

- Scenario 2 - This playbook queries the applications API endpoint. Application information, server clusters, scopes and policies are all reported on. Execute the playbook with -v to view all the API returned data.

- Scenario 3 - This playbook queries the flowsearch API endpoint. The usecase presented here is that of looking for latency metrics for connections between servers with App or Search in their name destined to the SQL02 server only. Execute the playbook with -v to view all the API returned data.

- Scenario 5 - This playbook queries the flowsearch/topn API endpoint. Data available is grouped by 'dimension' and sorted by 'metric' and the filters are the same as for the regular flowsearch queries. Execute the playbook with -v to view all the API returned data.


## Dependancies

- Ansible 2.8.x
- Python 3.7.x
- [tetpyclient](https://pypi.org/project/tetpyclient/) 


## Configuration / Getting Started

- Review the `vars` and `hosts` files update to refelect your Tetration deployment if not accessing the dCloud environment.

- Review the `output` directory for sample output from the Jinja2 templates

## Using dcloud's instant access lab

The dCloud instant access browser session is authenticated and sets cookies which are required
when making any calls to the Tetration dashboard (something in the path intercepts all connections). If those dcloud cookies are not in the requests the calls are redirected to a login page for dcloud.

To fix for development: in the `tetpyclient.py` file from the
`tetpyclient` package installed by pip, edit the `signed_http_request` function
and add the cookie header to all requests.

```
req.headers['Cookie'] = 'copy-paste cookie header from your browser (Inspect
page -> Network -> Copy headers'
```

Testing with python quickly:

```py
#! /usr/bin/env python3

from tetpyclient import RestClient

API_ENDPOINT="https://tetration.svpod.dc-01.com"

# credentials.json looks like:
# {
#   "api_key": "<hex string>",
#   "api_secret": "<hex string>"
# }

restclient = RestClient(API_ENDPOINT,
                credentials_file='api_credentials.json',
                verify=True)

# followed by API calls, for example API to retrieve list of agents.
# API can be passed /openapi/v1/applications or just /applications.
resp = restclient.get('/applications')

print(resp.text)
```
