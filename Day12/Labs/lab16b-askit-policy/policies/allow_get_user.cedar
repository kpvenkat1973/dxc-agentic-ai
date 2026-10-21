permit(
  principal,
  action == AgentCore::Action::"askit-lambda___get_user",
  resource == AgentCore::Gateway::"{{GATEWAY_ARN}}"
);
