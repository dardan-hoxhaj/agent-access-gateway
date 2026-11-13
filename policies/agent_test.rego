package agent.authz

import data.agent.authz

test_allow_ticket_read {
  authz.allow with input as {"agent_id": "ticket-agent", "tool": "tickets", "action": "read"}
}

test_allow_ticket_write {
  authz.allow with input as {"agent_id": "ticket-agent", "tool": "tickets", "action": "write"}
}

test_deny_billing_on_tickets {
  not authz.allow with input as {"agent_id": "billing-agent", "tool": "tickets", "action": "read"}
}

test_deny_unknown_agent {
  not authz.allow with input as {"agent_id": "stranger", "tool": "tickets", "action": "read"}
}

test_deny_missing_action {
  not authz.allow with input as {"agent_id": "ticket-agent", "tool": "tickets", "action": "delete"}
}
