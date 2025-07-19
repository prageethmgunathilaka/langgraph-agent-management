"""
Simple LLM-Powered Customer Support Demo
Demonstrates intelligent customer support responses using our LLM service.
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any

# Add the app directory to Python path for imports
sys.path.append('app')

try:
    from services.llm_service import LLMService, LLMServiceFactory, InferenceType
    LLM_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  LLM Service import failed: {e}")
    LLM_AVAILABLE = False

class SimpleLLMSupportDemo:
    """Simple demo of LLM-powered customer support responses."""
    
    def __init__(self):
        self.llm_service = None
        self._initialize_llm()
        
    def _initialize_llm(self):
        """Initialize LLM service for intelligent responses."""
        if not LLM_AVAILABLE:
            print("❌ LLM Service not available - import failed")
            return
            
        try:
            # Try to create LLM service from environment
            self.llm_service = LLMServiceFactory.create_from_env()
            print(f"✅ LLM Service initialized successfully")
            print(f"⚡ Provider: {self.llm_service.config.provider.value}")
            print(f"🎯 Model: {self.llm_service.config.model}")
        except Exception as e:
            print(f"⚠️  LLM Service not available: {e}")
            print("📝 Note: Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY for intelligent responses")
            self.llm_service = None
    
    def create_support_prompt(self, ticket: Dict[str, Any], agent_type: str) -> str:
        """Create specialized prompt for different agent types."""
        base_context = f"""
You are an expert {agent_type.replace('_', ' ')} agent in a customer support system.

Customer Information:
- Name: {ticket['customer']}
- Issue: {ticket['subject']}
- Description: {ticket['description']}
- Priority: {ticket['priority']}
- Metadata: {json.dumps(ticket.get('metadata', {}), indent=2)}

Provide a helpful, professional, and specific response to resolve this customer's issue.
Be empathetic, clear, and actionable in your response.
"""

        agent_prompts = {
            "technical": base_context + """
As a Technical Support Specialist:
- Analyze the technical issue in detail
- Provide step-by-step troubleshooting instructions
- Suggest specific solutions or workarounds
- Mention any known bugs or compatibility issues
- Recommend preventive measures
""",
            "billing": base_context + """
As a Billing Support Specialist:
- Review the billing concern carefully
- Explain the charges or refund process clearly
- Provide specific timeline expectations
- Offer account protection advice if relevant
- Ensure compliance with payment policies
""",
            "order": base_context + """
As an Order Status Specialist:
- Analyze the shipping/delivery situation
- Provide specific tracking information and next steps
- Coordinate with logistics partners if needed
- Offer alternative solutions (expedited shipping, etc.)
- Set clear expectations for resolution timeline
""",
            "escalation": base_context + """
As an Escalation Specialist:
- Assess the severity and complexity of the issue
- Coordinate with appropriate teams (security, legal, management)
- Provide immediate protective measures if needed
- Ensure customer safety and data protection
- Set expectations for high-priority resolution process
"""
        }
        
        return agent_prompts.get(agent_type, base_context)
    
    async def generate_intelligent_response(self, ticket: Dict[str, Any], agent_type: str) -> str:
        """Generate intelligent response using LLM."""
        if not self.llm_service:
            return self._get_demo_response(ticket, agent_type)
            
        try:
            # Create context-aware prompt
            prompt = self.create_support_prompt(ticket, agent_type)
            
            # Generate response using LLM
            response = await self.llm_service.dynamic_inference(
                situation=f"Customer support ticket requiring {agent_type} expertise",
                context={
                    "prompt": prompt,
                    "ticket": ticket,
                    "agent_type": agent_type,
                    "temperature": 0.7
                },
                inference_type=InferenceType.DYNAMIC
            )
            
            if response.success:
                return response.content
            else:
                print(f"⚠️  LLM generation failed: {response.error}")
                return self._get_demo_response(ticket, agent_type)
                
        except Exception as e:
            print(f"❌ Error generating intelligent response: {e}")
            return self._get_demo_response(ticket, agent_type)
    
    def _get_demo_response(self, ticket: Dict[str, Any], agent_type: str) -> str:
        """Get demo response when LLM is not available."""
        demo_responses = {
            "technical": f"""
Dear {ticket['customer']},

Thank you for reporting this technical issue. I've analyzed your app crash problem with large file uploads.

**Issue Analysis:**
Based on your description, this appears to be a memory management issue affecting files larger than 100MB on both iOS and Android versions.

**Immediate Solution:**
1. Please update to the latest app version (2.1.5) which includes memory optimization fixes
2. Clear your app cache: Settings > Storage > Clear Cache
3. Restart your device to free up memory

**Preventive Measures:**
- Compress large files before uploading when possible
- Upload files during off-peak hours for better performance
- Ensure you have at least 2GB free storage space

**Next Steps:**
If the issue persists after updating, please contact us with your device logs. We're committed to resolving this quickly as we understand it's blocking your work.

Best regards,
Technical Support Team
""",
            
            "billing": f"""
Dear {ticket['customer']},

I sincerely apologize for the billing inconvenience you've experienced.

**Issue Identified:**
I've located the duplicate charge of $29.99 on your account from January 15th. This appears to be a system processing error.

**Resolution:**
- Refund of $29.99 has been initiated immediately
- You'll see the credit on your statement within 3-5 business days
- Your subscription remains active with no interruption

**Account Protection:**
I've also added a note to your account to prevent similar issues in the future.

**Confirmation:**
You'll receive an email confirmation of this refund within the next hour.

Thank you for your patience, and again, I apologize for any budget concerns this may have caused.

Best regards,
Billing Support Team
""",
            
            "order": f"""
Dear {ticket['customer']},

I understand your concern about your laptop order being shipped to the wrong address, and I'm here to help resolve this immediately.

**Current Status:**
I've tracked your order #ORD-12345 and confirmed it was shipped to your old address on 123 Old Street.

**Immediate Action:**
- I've contacted our logistics partner to intercept the package
- The package has been successfully rerouted to your correct address: 456 New Avenue, City B
- New tracking number: 1Z999AA1234567890-REDIRECT

**Security Measures:**
Given the valuable nature of your laptop, I've:
- Flagged the package for signature required delivery
- Added delivery instructions to call you before delivery
- Updated your address permanently in our system

**New Delivery:**
Expected delivery: Tomorrow by 5 PM

You'll receive SMS and email updates throughout the delivery process.

Best regards,
Order Status Team
""",
            
            "escalation": f"""
Dear {ticket['customer']},

I'm treating your account security concern with the highest priority and have immediately escalated this to our security team.

**Immediate Actions Taken:**
- Your account has been temporarily secured and all sessions terminated
- All stored payment methods have been protected
- Suspicious IP addresses have been blocked: 192.168.1.100, 10.0.0.50, 203.45.67.89

**Security Review:**
Our security specialist is conducting a comprehensive review of:
- All recent account activity
- Potential data access
- System vulnerability assessment

**Next Steps:**
- You'll receive a call from our security team within 1 hour
- We'll provide a detailed security report within 24 hours
- New security measures will be implemented on your account

**Your Data:**
Rest assured, we're treating this with utmost seriousness given your $5,000+ in stored data and transaction history.

Thank you for reporting this promptly. Your vigilance helps us protect all our customers.

Best regards,
Security Escalation Team
"""
        }
        
        return demo_responses.get(agent_type, f"Processing your {agent_type} request...")
    
    async def demo_intelligent_support(self):
        """Run the intelligent support demo."""
        print("🧠 LLM-Powered Customer Support Demo")
        print("=" * 60)
        
        # Sample tickets
        tickets = [
            {
                "id": "TECH-001",
                "customer": "John Smith",
                "subject": "App crashes when uploading large files",
                "description": "Every time I try to upload files larger than 100MB, the mobile app crashes immediately. This happens on both my iPhone 14 Pro and iPad. I've tried reinstalling the app but the problem persists.",
                "priority": "high",
                "category": "technical",
                "metadata": {
                    "device": "iPhone 14 Pro, iPad Pro",
                    "app_version": "2.1.4",
                    "file_size": "100MB+",
                    "error_frequency": "always"
                }
            },
            {
                "id": "BILL-002", 
                "customer": "Sarah Johnson",
                "subject": "Charged twice for monthly subscription",
                "description": "I noticed two identical charges of $29.99 on my credit card statement for the same day. I need this resolved quickly as it's affecting my budget.",
                "priority": "medium",
                "category": "billing",
                "metadata": {
                    "charge_amount": "$29.99",
                    "charge_date": "2025-01-15",
                    "duplicate_charges": 2
                }
            }
        ]
        
        for ticket in tickets:
            await self._process_ticket_with_llm(ticket)
            print("\n" + "="*80 + "\n")
    
    async def _process_ticket_with_llm(self, ticket: Dict[str, Any]):
        """Process a ticket with LLM intelligence."""
        print(f"🎫 Ticket: {ticket['id']}")
        print(f"👤 Customer: {ticket['customer']}")
        print(f"📋 Subject: {ticket['subject']}")
        print(f"⚡ Priority: {ticket['priority'].upper()}")
        print(f"🔍 Category: {ticket['category'].title()}")
        
        print(f"\n🤖 Generating intelligent response...")
        
        # Map category to agent type
        agent_mapping = {
            "technical": "technical",
            "billing": "billing",
            "order_status": "order",
            "escalation": "escalation"
        }
        
        agent_type = agent_mapping.get(ticket["category"], "technical")
        
        # Generate intelligent response
        response = await self.generate_intelligent_response(ticket, agent_type)
        
        print(f"\n💬 {'LLM-Generated' if self.llm_service else 'Demo'} Response:")
        print("─" * 60)
        print(response)
        print("─" * 60)
        
        if self.llm_service:
            print(f"✅ Response generated using {self.llm_service.config.provider.value} {self.llm_service.config.model}")
        else:
            print("📝 Demo response shown (LLM not available)")

async def main():
    """Run the simple LLM support demo."""
    print("🚀 Simple LLM-Powered Customer Support Demo")
    print("Demonstrating intelligent customer support responses")
    print("=" * 80)
    
    demo = SimpleLLMSupportDemo()
    await demo.demo_intelligent_support()
    
    print("🎉 Demo Complete!")
    print("\n💡 This demonstrates:")
    print("   • LLM-powered intelligent customer support responses")
    print("   • Context-aware problem analysis and solutions")
    print("   • Professional, empathetic customer communication")
    print("   • Specialized responses for different support categories")

if __name__ == "__main__":
    asyncio.run(main()) 