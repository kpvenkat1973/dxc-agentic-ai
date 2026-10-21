permit(
  principal,
  action == AgentCore::Action::"askit-lambda___get_ticket",
  resource == AgentCore::Gateway::"{{GATEWAY_ARN}}"
);
