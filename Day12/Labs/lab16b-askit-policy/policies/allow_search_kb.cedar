permit(
  principal,
  action == AgentCore::Action::"askit-lambda___search_kb",
  resource == AgentCore::Gateway::"{{GATEWAY_ARN}}"
);
