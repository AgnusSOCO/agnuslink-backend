import openai
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class AIService:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_API_BASE')
        )
    
    def score_lead_quality(self, lead_data: Dict) -> Dict:
        """
        Analyze lead quality and provide a score with recommendations
        Cost: ~$0.001-0.002 per lead analysis
        """
        try:
            prompt = f"""
            Analyze this lead for quality and conversion potential. Provide a score from 1-100 and specific recommendations.

            Lead Information:
            - Name: {lead_data.get('full_name', 'N/A')}
            - Email: {lead_data.get('email', 'N/A')}
            - Phone: {lead_data.get('phone', 'N/A')}
            - Address: {lead_data.get('address', 'N/A')}, {lead_data.get('city', 'N/A')}, {lead_data.get('state', 'N/A')}
            - Lead Type: {lead_data.get('lead_type', 'N/A')}
            - Notes: {lead_data.get('notes', 'N/A')}

            Respond in JSON format:
            {{
                "score": <number 1-100>,
                "quality_level": "<high|medium|low>",
                "conversion_probability": "<percentage>",
                "recommendations": [
                    "specific recommendation 1",
                    "specific recommendation 2"
                ],
                "red_flags": [
                    "potential issue 1 if any"
                ],
                "next_steps": [
                    "suggested action 1",
                    "suggested action 2"
                ]
            }}
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert lead qualification specialist for home improvement services. Analyze leads based on completeness of information, geographic factors, and industry best practices."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )

            result = json.loads(response.choices[0].message.content)
            result['analyzed_at'] = datetime.utcnow().isoformat()
            return result

        except Exception as e:
            return {
                "score": 50,
                "quality_level": "medium",
                "conversion_probability": "Unknown",
                "recommendations": ["Manual review required"],
                "red_flags": [f"AI analysis failed: {str(e)}"],
                "next_steps": ["Review lead manually"],
                "analyzed_at": datetime.utcnow().isoformat()
            }

    def generate_follow_up_suggestions(self, lead_data: Dict, lead_status: str) -> List[str]:
        """
        Generate personalized follow-up suggestions based on lead data and status
        Cost: ~$0.001 per suggestion generation
        """
        try:
            prompt = f"""
            Generate 3-5 specific follow-up suggestions for this lead based on their status and information.

            Lead Status: {lead_status}
            Lead Type: {lead_data.get('lead_type', 'N/A')}
            Location: {lead_data.get('city', 'N/A')}, {lead_data.get('state', 'N/A')}
            Notes: {lead_data.get('notes', 'N/A')}

            Provide actionable, specific suggestions that an affiliate can use to improve conversion.
            Focus on timing, communication methods, and value propositions.

            Return as a JSON array of strings:
            ["suggestion 1", "suggestion 2", "suggestion 3"]
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a sales expert specializing in home improvement lead conversion. Provide specific, actionable follow-up strategies."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.5
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            return [
                "Follow up within 24 hours with a personalized message",
                "Provide relevant case studies or testimonials",
                "Schedule a consultation call to discuss their specific needs"
            ]

    def analyze_affiliate_performance(self, affiliate_data: Dict) -> Dict:
        """
        Analyze affiliate performance and provide insights and recommendations
        Cost: ~$0.002-0.003 per analysis
        """
        try:
            prompt = f"""
            Analyze this affiliate's performance and provide insights and recommendations for improvement.

            Affiliate Performance Data:
            - Total Leads: {affiliate_data.get('total_leads', 0)}
            - Conversion Rate: {affiliate_data.get('conversion_rate', 0)}%
            - Total Earnings: ${affiliate_data.get('total_earnings', 0)}
            - Active Days: {affiliate_data.get('active_days', 0)}
            - Referrals: {affiliate_data.get('referral_count', 0)}
            - Lead Types: {affiliate_data.get('lead_types', [])}
            - Geographic Focus: {affiliate_data.get('locations', [])}

            Respond in JSON format:
            {{
                "performance_rating": "<excellent|good|average|needs_improvement>",
                "strengths": [
                    "strength 1",
                    "strength 2"
                ],
                "improvement_areas": [
                    "area 1",
                    "area 2"
                ],
                "recommendations": [
                    "specific recommendation 1",
                    "specific recommendation 2"
                ],
                "growth_opportunities": [
                    "opportunity 1",
                    "opportunity 2"
                ],
                "predicted_monthly_potential": "<estimated monthly earnings>"
            }}
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a business performance analyst specializing in affiliate marketing and lead generation. Provide data-driven insights and actionable recommendations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.3
            )

            result = json.loads(response.choices[0].message.content)
            result['analyzed_at'] = datetime.utcnow().isoformat()
            return result

        except Exception as e:
            return {
                "performance_rating": "average",
                "strengths": ["Consistent activity"],
                "improvement_areas": ["Lead quality", "Follow-up timing"],
                "recommendations": ["Focus on higher-quality leads", "Improve follow-up processes"],
                "growth_opportunities": ["Expand to new lead types", "Build referral network"],
                "predicted_monthly_potential": "Analysis unavailable",
                "analyzed_at": datetime.utcnow().isoformat()
            }

    def generate_marketing_content(self, content_type: str, target_audience: str, lead_type: str) -> str:
        """
        Generate marketing content for affiliates
        Cost: ~$0.002-0.005 per content generation
        """
        try:
            prompt = f"""
            Generate {content_type} content for affiliate marketing in the {lead_type} industry.
            
            Target Audience: {target_audience}
            Lead Type: {lead_type}
            Content Type: {content_type}

            Requirements:
            - Professional and trustworthy tone
            - Include value proposition
            - Call-to-action
            - Appropriate length for the content type
            - Compliance-friendly (no unrealistic promises)

            Generate engaging, conversion-focused content.
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional copywriter specializing in home improvement and service industry marketing. Create compliant, effective marketing content."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"Content generation temporarily unavailable. Please try again later. Error: {str(e)}"

    def predict_lead_conversion_time(self, lead_data: Dict, historical_data: List[Dict]) -> Dict:
        """
        Predict when a lead is likely to convert based on historical patterns
        Cost: ~$0.001-0.002 per prediction
        """
        try:
            # Prepare historical data summary
            if historical_data:
                avg_conversion_time = sum([h.get('conversion_days', 0) for h in historical_data]) / len(historical_data)
                conversion_rate = len([h for h in historical_data if h.get('converted', False)]) / len(historical_data)
            else:
                avg_conversion_time = 14
                conversion_rate = 0.25

            prompt = f"""
            Predict the conversion timeline for this lead based on historical data and lead characteristics.

            Lead Information:
            - Lead Type: {lead_data.get('lead_type', 'N/A')}
            - Location: {lead_data.get('city', 'N/A')}, {lead_data.get('state', 'N/A')}
            - Contact Quality: {lead_data.get('phone', 'N/A') and lead_data.get('email', 'N/A')}
            - Notes: {lead_data.get('notes', 'N/A')}

            Historical Context:
            - Average Conversion Time: {avg_conversion_time} days
            - Overall Conversion Rate: {conversion_rate:.2%}
            - Sample Size: {len(historical_data)} leads

            Respond in JSON format:
            {{
                "predicted_conversion_days": <number>,
                "conversion_probability": "<percentage>",
                "optimal_follow_up_schedule": [
                    "Day 1: Initial contact",
                    "Day 3: Follow-up call",
                    "Day 7: Value-add email"
                ],
                "urgency_level": "<high|medium|low>",
                "reasoning": "Brief explanation of the prediction"
            }}
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a data analyst specializing in sales conversion predictions. Use historical patterns and lead characteristics to make accurate predictions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.3
            )

            result = json.loads(response.choices[0].message.content)
            result['predicted_at'] = datetime.utcnow().isoformat()
            return result

        except Exception as e:
            return {
                "predicted_conversion_days": 14,
                "conversion_probability": "25%",
                "optimal_follow_up_schedule": [
                    "Day 1: Initial contact within 24 hours",
                    "Day 3: Follow-up call or email",
                    "Day 7: Value-add content or testimonial"
                ],
                "urgency_level": "medium",
                "reasoning": "Based on industry averages",
                "predicted_at": datetime.utcnow().isoformat()
            }

    def generate_smart_insights(self, platform_data: Dict) -> Dict:
        """
        Generate platform-wide insights and recommendations for admins
        Cost: ~$0.003-0.005 per analysis
        """
        try:
            prompt = f"""
            Analyze this affiliate platform data and provide strategic insights and recommendations.

            Platform Metrics:
            - Total Affiliates: {platform_data.get('total_affiliates', 0)}
            - Active Affiliates: {platform_data.get('active_affiliates', 0)}
            - Total Leads: {platform_data.get('total_leads', 0)}
            - Conversion Rate: {platform_data.get('conversion_rate', 0)}%
            - Average Lead Value: ${platform_data.get('avg_lead_value', 0)}
            - Top Lead Types: {platform_data.get('top_lead_types', [])}
            - Growth Rate: {platform_data.get('growth_rate', 0)}%

            Respond in JSON format:
            {{
                "platform_health": "<excellent|good|concerning|critical>",
                "key_insights": [
                    "insight 1",
                    "insight 2"
                ],
                "growth_opportunities": [
                    "opportunity 1",
                    "opportunity 2"
                ],
                "risk_factors": [
                    "risk 1 if any"
                ],
                "strategic_recommendations": [
                    "recommendation 1",
                    "recommendation 2"
                ],
                "predicted_trends": [
                    "trend 1",
                    "trend 2"
                ]
            }}
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a business intelligence analyst specializing in affiliate marketing platforms. Provide strategic insights based on platform metrics."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=700,
                temperature=0.3
            )

            result = json.loads(response.choices[0].message.content)
            result['generated_at'] = datetime.utcnow().isoformat()
            return result

        except Exception as e:
            return {
                "platform_health": "good",
                "key_insights": ["Platform showing steady growth", "Affiliate engagement is stable"],
                "growth_opportunities": ["Expand lead types", "Improve affiliate training"],
                "risk_factors": ["Monitor conversion rates"],
                "strategic_recommendations": ["Focus on affiliate retention", "Optimize lead quality"],
                "predicted_trends": ["Continued growth expected"],
                "generated_at": datetime.utcnow().isoformat()
            }

