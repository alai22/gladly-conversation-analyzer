#!/bin/bash
# Add new SSH key to authorized_keys
echo "ssh-rsa YOUR_SSH_PUBLIC_KEY_HERE user@hostname" >> /home/ec2-user/.ssh/authorized_keys
chmod 600 /home/ec2-user/.ssh/authorized_keys
chown ec2-user:ec2-user /home/ec2-user/.ssh/authorized_keys

