"""
Email Notification Service
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending email notifications"""
    
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('SMTP_FROM_EMAIL', self.smtp_username)
        self.enabled = os.getenv('EMAIL_NOTIFICATIONS_ENABLED', 'false').lower() in ('true', '1', 'yes')
        
    def is_configured(self) -> bool:
        """Check if email service is properly configured"""
        if not self.enabled:
            return False
        if not self.smtp_username or not self.smtp_password:
            return False
        return True
    
    def send_notification(self, 
                         to_email: str,
                         subject: str,
                         body: str,
                         html_body: Optional[str] = None) -> bool:
        """
        Send an email notification
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML email body
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.debug("Email notifications not configured or disabled")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add plain text part
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def send_download_completion_notification(self,
                                            to_email: str,
                                            batch_size: int,
                                            downloaded_count: int,
                                            failed_count: int,
                                            elapsed_time_seconds: Optional[float] = None,
                                            date_range: Optional[tuple] = None,
                                            error: Optional[str] = None) -> bool:
        """
        Send a notification when a download batch completes
        
        Args:
            to_email: Recipient email address
            batch_size: Requested batch size
            downloaded_count: Number of conversations successfully downloaded
            failed_count: Number of conversations that failed to download
            elapsed_time_seconds: Total time taken in seconds
            date_range: Optional tuple of (start_date, end_date)
            error: Optional error message if download failed
            
        Returns:
            True if email sent successfully, False otherwise
        """
        # Format elapsed time
        elapsed_str = "N/A"
        if elapsed_time_seconds:
            hours = int(elapsed_time_seconds // 3600)
            minutes = int((elapsed_time_seconds % 3600) // 60)
            seconds = int(elapsed_time_seconds % 60)
            if hours > 0:
                elapsed_str = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                elapsed_str = f"{minutes}m {seconds}s"
            else:
                elapsed_str = f"{seconds}s"
        
        # Build subject
        if error:
            subject = f"⚠️ Gladly Download Failed - {failed_count} failed"
        else:
            subject = f"✅ Gladly Download Complete - {downloaded_count} conversations"
        
        # Build plain text body
        body_lines = [
            "Gladly Conversation Download Status",
            "=" * 40,
            "",
            f"Status: {'❌ Failed' if error else '✅ Success'}",
            f"Requested Batch Size: {batch_size:,}",
            f"Downloaded: {downloaded_count:,}",
            f"Failed: {failed_count:,}",
            f"Elapsed Time: {elapsed_str}",
        ]
        
        if date_range:
            start_date, end_date = date_range
            body_lines.append(f"Date Range: {start_date} to {end_date}")
        
        if error:
            body_lines.extend([
                "",
                f"Error: {error}"
            ])
        else:
            success_rate = (downloaded_count / batch_size * 100) if batch_size > 0 else 0
            body_lines.extend([
                "",
                f"Success Rate: {success_rate:.1f}%"
            ])
        
        body_lines.extend([
            "",
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "You can view the full download history in the Download Manager."
        ])
        
        body = "\n".join(body_lines)
        
        # Build HTML body
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: {'#d32f2f' if error else '#2e7d32'};">Gladly Conversation Download Status</h2>
            <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
              <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Status:</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; color: {'#d32f2f' if error else '#2e7d32'};">
                  {'❌ Failed' if error else '✅ Success'}
                </td>
              </tr>
              <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Requested Batch Size:</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{batch_size:,}</td>
              </tr>
              <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Downloaded:</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; color: #2e7d32;">{downloaded_count:,}</td>
              </tr>
              <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Failed:</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; color: {'#d32f2f' if failed_count > 0 else '#666'};">{failed_count:,}</td>
              </tr>
              <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Elapsed Time:</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{elapsed_str}</td>
              </tr>
        """
        
        if date_range:
            start_date, end_date = date_range
            html_body += f"""
              <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Date Range:</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{start_date} to {end_date}</td>
              </tr>
            """
        
        if error:
            html_body += f"""
              <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold; color: #d32f2f;">Error:</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; color: #d32f2f;">{error}</td>
              </tr>
            """
        else:
            success_rate = (downloaded_count / batch_size * 100) if batch_size > 0 else 0
            html_body += f"""
              <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Success Rate:</td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">{success_rate:.1f}%</td>
              </tr>
            """
        
        html_body += f"""
            </table>
            <p style="margin-top: 20px; color: #666; font-size: 0.9em;">
              Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
              You can view the full download history in the Download Manager.
            </p>
          </body>
        </html>
        """
        
        return self.send_notification(to_email, subject, body, html_body)

