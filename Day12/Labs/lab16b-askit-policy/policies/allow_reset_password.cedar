permit(
  principal,
  action == AgentCore::Action::"askit-lambda___reset_password",
  resource == AgentCore::Gateway::"{{GATEWAY_ARN}}"
);
