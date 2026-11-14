package agent.authz

import data.agent.authz
import rego.v1

test_allow_ticket_read if {
	authz.allow with input as {"agent_id": "ticket-agent", "tool": "tickets", "action": "read"}
}

test_allow_ticket_write if {
	authz.allow with input as {"agent_id": "ticket-agent", "tool": "tickets", "action": "write"}
}

test_deny_billing_on_tickets if {
	not authz.allow with input as {"agent_id": "billing-agent", "tool": "tickets", "action": "read"}
}

test_deny_unknown_agent if {
	not authz.allow with input as {"agent_id": "stranger", "tool": "tickets", "action": "read"}
}

test_deny_missing_action if {
	not authz.allow with input as {"agent_id": "ticket-agent", "tool": "tickets", "action": "delete"}
}
