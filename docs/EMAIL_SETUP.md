# Email Notification Setup Guide

## Gmail Setup Instructions

The email notification feature uses SMTP to send notifications when download batches complete. For Gmail accounts, you need to use an **App Password** (not your regular password).

### Step 1: Enable 2-Step Verification

1. Go to your [Google Account Security settings](https://myaccount.google.com/security)
2. Under "Signing in to Google", enable **2-Step Verification** if not already enabled
3. Follow the prompts to complete setup

### Step 2: Generate an App Password

1. Go to [App Passwords](https://myaccount.google.com/apppasswords)
   - If you can't find this link, you may need to:
     - Search for "app passwords" in your Google Account settings
     - Or go to: Google Account → Security → 2-Step Verification → App passwords
2. Select "Mail" as the app
3. Select "Other (Custom name)" as the device
4. Enter a name like "Gladly Download Manager"
5. Click "Generate"
6. **Copy the 16-character password** (you'll only see it once)

### Step 3: Configure Environment Variables

Add these to your `.env` file:

```bash
EMAIL_NOTIFICATIONS_ENABLED=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # The 16-character app password (remove spaces or keep them)
SMTP_FROM_EMAIL=your-email@gmail.com
```

**Important Notes:**
- Use the **16-character app password**, not your regular Gmail password
- The app password can include spaces - they'll be automatically handled
- Keep your app password secure - don't commit it to version control

### Alternative: Other Email Providers

For other email providers, adjust the settings:

**Outlook/Hotmail:**
```bash
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
```

**Yahoo:**
```bash
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
# Note: Yahoo also requires an app password
```

**Custom SMTP Server:**
- Check with your email provider for SMTP settings
- May need different ports (587 for TLS, 465 for SSL)

### Testing

To verify email notifications are working:
1. Start a small download batch (e.g., 10 conversations)
2. Wait for it to complete
3. Check your inbox at `alai@halocollar.com`

If emails aren't being sent:
- Check server logs for email errors
- Verify all environment variables are set correctly
- Ensure `EMAIL_NOTIFICATIONS_ENABLED=true`
- Verify the app password is correct (no extra spaces/characters)

