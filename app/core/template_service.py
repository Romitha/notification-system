from typing import Dict, Any, Optional
import re


class TemplateService:
    """Service for managing email templates"""

    async def get_template(self, template_id: str) -> Dict[str, Any]:
        """
        Get a template by ID
        This would typically fetch from a database or Drupal CMS
        """
        # Placeholder implementation - in reality, this would fetch from DB or CMS
        templates = {
            "welcome": {
                "subject": "Welcome to our service",
                "content": "Hello {{name}},\n\nWelcome to our service! We're excited to have you on board.\n\nRegards,\nThe Team"
            },
            "password_reset": {
                "subject": "Password Reset Request",
                "content": "Hello {{name}},\n\nYou have requested a password reset. Click the link below to reset your password:\n\n{{reset_link}}\n\nRegards,\nThe Team"
            },
            "notification": {
                "subject": "New Notification",
                "content": "Hello {{name}},\n\n{{message}}\n\nRegards,\nThe Team"
            }
        }

        if template_id not in templates:
            # Return default template if requested template not found
            return templates["notification"]

        return templates[template_id]

    async def apply_template(self, template: Dict[str, Any], content: str, metadata: Dict[str, Any]) -> str:
        """Apply template with variables from metadata"""
        template_content = template["content"]

        # Simple variable replacement
        for key, value in metadata.items():
            placeholder = "{{" + key + "}}"
            template_content = template_content.replace(placeholder, str(value))

        # If content was provided, replace {{message}} with it
        if content:
            template_content = template_content.replace("{{message}}", content)

        # Replace any remaining placeholders with empty strings
        template_content = re.sub(r'{{[^}]+}}', '', template_content)

        return template_content