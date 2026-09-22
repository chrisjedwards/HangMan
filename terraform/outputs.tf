output "public_ip" {
  description = "Public IP address of the Hangman EC2 instance."
  value       = aws_instance.hangman.public_ip
}

output "app_url" {
  description = "Ready-to-use URL for the deployed app. Allow 5-10 minutes after apply for cloud-init to finish before this responds."
  value       = "http://${aws_instance.hangman.public_ip}/"
}
