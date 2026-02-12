# AWS Security Group Configuration Guide

## Required Ports

To allow public access to the application, you need to configure Security Group rules in the AWS EC2 console.

### Inbound Rules

| Type | Protocol | Port Range | Source | Description |
|------|----------|-----------|--------|-------------|
| HTTP | TCP | 80 | 0.0.0.0/0 | Allow all HTTP access |
| SSH | TCP | 22 | Your IP / 0.0.0.0/0 | SSH remote access (recommend restricting to your IP) |

### Optional Configuration

If HTTPS is needed in the future:

| Type | Protocol | Port Range | Source | Description |
|------|----------|-----------|--------|-------------|
| HTTPS | TCP | 443 | 0.0.0.0/0 | Allow all HTTPS access |

## Configuration Steps

### Method 1: Via AWS Console

1. Log in to the AWS Console
2. Navigate to EC2 service
3. Select "Instances" in the left menu
4. Select your EC2 instance
5. Click the "Security" tab below
6. Click the Security Group name (blue link)
7. Click "Edit inbound rules"
8. Click "Add rule"
9. Configure the rule:
   - Type: HTTP
   - Protocol: TCP
   - Port Range: 80
   - Source: 0.0.0.0/0
   - Description: Allow HTTP traffic
10. Click "Save rules"

### Method 2: Via AWS CLI

```bash
# Get the Security Group ID
SECURITY_GROUP_ID=$(aws ec2 describe-instances \
    --instance-ids $(ec2-metadata --instance-id | cut -d " " -f 2) \
    --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
    --output text)

# Add HTTP rule
aws ec2 authorize-security-group-ingress \
    --group-id $SECURITY_GROUP_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0
```

## Verification

After configuration, verify with the following:

```bash
# Get public IP
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

# Test HTTP access
curl -I http://$PUBLIC_IP

# If you get HTTP/1.1 200 OK or another HTTP status code, the configuration is successful
```

## Security Recommendations

1. **Restrict SSH access**: It's recommended to limit the SSH (port 22) source IP to your office network or VPN IP, rather than 0.0.0.0/0
2. **Consider using HTTPS**: For production environments, configure an SSL certificate for encrypted communication
3. **Review rules regularly**: Periodically check and clean up unnecessary Security Group rules
4. **Use descriptions**: Add clear descriptions to each rule for easier management

## Configuring HTTPS (Optional)

If HTTPS is needed, you can use free Let's Encrypt certificates:

```bash
# Install Certbot
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate (replace your-domain.com with your domain)
sudo certbot --nginx -d your-domain.com

# Certbot will automatically configure Nginx and restart the service
```

Note: Using Let's Encrypt requires:
1. A domain name pointing to your EC2 public IP
2. Security Group has ports 80 and 443 open
3. Nginx is running
