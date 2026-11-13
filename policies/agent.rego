package agent.authz

default allow = false

# Deny by default. Allow only when the agent is explicitly granted
# this tool and action in data.agents.
allow {
  data.agents[input.agent_id][input.tool][input.action] == true
}
