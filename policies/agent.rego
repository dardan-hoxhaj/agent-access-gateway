package agent.authz

import rego.v1

default allow := false

# Deny by default. Allow only when the agent is explicitly granted
# this tool and action in data.agents.
allow if {
	data.agents[input.agent_id][input.tool][input.action] == true
}
