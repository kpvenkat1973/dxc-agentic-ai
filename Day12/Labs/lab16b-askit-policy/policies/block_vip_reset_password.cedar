forbid(
  principal,
  action == AgentCore::Action::"askit-lambda___reset_password",
  resource == AgentCore::Gateway::"{{GATEWAY_ARN}}"
)
when {
  ["EMP-1001", "EMP-1012", "EMP-1023"].contains(context.input.user_id)
};
